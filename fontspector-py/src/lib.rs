use std::{collections::HashMap, env, path::Path, vec};
// Provide an environment where we can run fontbakery tests
// as-is, but have them call a Rust implementation underneath
use fontspector_checkapi::{
    CheckImplementation, Context, Plugin, Registry, StatusCode, Testable, TestableCollection,
    TestableType,
};
use profile_googlefonts::GoogleFonts;
use profile_opentype::OpenType;
use profile_universal::Universal;
use profile_fontwerk::Fontwerk;
use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyDict, PyDictMethods, PyList, PyString, PyTuple},
};
use pythonize::depythonize;

#[pyclass]
struct CheckTester {
    check_id: String,
    profile: Option<String>,
}

fn obj_to_testable(py: Python, arg: &Bound<'_, PyAny>) -> PyResult<Testable> {
    let ttfont_class = py.import("fontTools.ttLib")?.getattr("TTFont")?;
    // if it's a string, just return a new testable
    if arg.is_instance_of::<PyString>() {
        let filename: String = arg.extract()?;
        return Testable::new(&filename)
            .map_err(|e| PyValueError::new_err(format!("Couldn't create testable object: {}", e)));
    }
    if !arg.is_instance(&ttfont_class)? {
        panic!("I can't handle args {:?}", arg);
    }
    let filename: String = arg
        .getattr("reader")?
        .getattr("file")?
        .getattr("name")?
        .extract()?;
    let basename = Path::new(&filename)
        .file_name()
        .ok_or_else(|| PyValueError::new_err("Couldn't extract basename from filename"))?;
    let tempfile = env::temp_dir().join(basename);
    let tempfile = tempfile
        .to_str()
        .ok_or_else(|| PyValueError::new_err("Couldn't convert tempfile path to string"))?;
    arg.call_method1("save", (tempfile,))?;
    let testable = Testable::new(tempfile)
        .map_err(|e| PyValueError::new_err(format!("Couldn't create testable object: {}", e)))?;
    Ok(testable)
}

#[pymethods]
impl CheckTester {
    #[new]
    #[pyo3(signature = (check_id, profile=None))]
    fn new(check_id: String, profile: Option<String>) -> Self {
        Self { check_id, profile }
    }

    #[pyo3(signature = (*args, **kwargs))]
    fn __call__<'a>(
        &self,
        py: Python<'a>,
        args: &Bound<'a, PyTuple>,
        kwargs: Option<&Bound<'a, PyDict>>,
    ) -> PyResult<Vec<Bound<'a, PyAny>>> {
        // Spin up a new fontspector (each time, how extravagant)
        let mut registry = Registry::new();
        OpenType.register(&mut registry).map_err(|_| {
            PyValueError::new_err("Couldn't register opentype profile, fontspector bug")
        })?;
        Universal.register(&mut registry).map_err(|_| {
            PyValueError::new_err("Couldn't register universal profile, fontspector bug")
        })?;
        GoogleFonts.register(&mut registry).map_err(|_| {
            PyValueError::new_err("Couldn't register Google Fonts profile, fontspector bug")
        })?;
        Fontwerk.register(&mut registry).map_err(|_| {
            PyValueError::new_err("Couldn't register Fontwerk profile, fontspector bug")
        })?;

        let check = registry
            .checks
            .get(&self.check_id)
            .ok_or_else(|| PyValueError::new_err("Check not found"))?;

        // We have almost certainly been handed a TTFont object. Turn it into a testable
        let first_arg = args
            .get_item(0)
            .map_err(|_| PyValueError::new_err("No args found"))?;
        let testables = if first_arg.is_instance_of::<PyList>() {
            let first_arg: &Bound<PyList> = first_arg.downcast()?;
            first_arg
                .iter()
                .map(|a| obj_to_testable(py, &a))
                .collect::<Result<Vec<_>, _>>()?
        } else {
            vec![obj_to_testable(py, &first_arg)?]
        };
        let collection = TestableCollection {
            testables,
            directory: "".to_string(),
        };
        let newargs = if matches!(check.implementation, CheckImplementation::CheckOne(_)) {
            let first = &collection
                .testables
                .first()
                .ok_or_else(|| PyValueError::new_err("No testables found in the collection"))?;
            TestableType::Single(first)
        } else {
            TestableType::Collection(&collection)
        };

        let mut fontspector_config = HashMap::new();
        let mut skip_network = false;

        if let Some(kwargs) = kwargs {
            if let Some(config) = kwargs.get_item("config")? {
                fontspector_config = depythonize(&config)?;
            }
            if let Some(skip_network_arg) = kwargs.get_item("skip_network")? {
                skip_network = skip_network_arg.as_any().extract()?;
            }
        }

        let mut context = Context {
            configuration: fontspector_config,
            full_lists: true,
            skip_network,
            ..Default::default()
        };
        if let Some(profile_name) = &self.profile {
            let profile = registry.get_profile(profile_name).ok_or_else(|| {
                PyValueError::new_err(format!("Profile {} not found", profile_name))
            })?;
            context = context.specialize(check, &context.configuration, profile);
        }

        // Run the check!
        let result = check
            .run(&newargs, &context, None)
            .ok_or_else(|| PyValueError::new_err("No results returned?"))?;
        // Map results back to a Python list of subresults
        let status_module = py.import("fontbakery.status")?;
        let subresult_module = py.import("fontbakery.result")?;
        let message_class = py.import("fontbakery.message")?.getattr("Message")?;
        let mut py_subresults = vec![];
        for subresult in result.subresults {
            let severity = match subresult.severity {
                StatusCode::Skip => status_module.getattr("SKIP")?,
                StatusCode::Info => status_module.getattr("INFO")?,
                StatusCode::Warn => status_module.getattr("WARN")?,
                StatusCode::Pass => status_module.getattr("PASS")?,
                StatusCode::Fail => status_module.getattr("FAIL")?,
                StatusCode::Error => status_module.getattr("ERROR")?,
            };
            let message = message_class.call1((
                subresult.code.unwrap_or("None".to_string()),
                subresult.message.unwrap_or("No message".to_string()),
            ))?;
            py_subresults.push(
                subresult_module
                    .getattr("Subresult")?
                    .call1((severity, message))?,
            )
        }
        Ok(py_subresults)
    }
}

#[pyfunction]
fn registered_checks() -> PyResult<Vec<String>> {
    let mut registry = Registry::new();
    OpenType.register(&mut registry).map_err(|_| {
        PyValueError::new_err("Couldn't register opentype profile, fontspector bug")
    })?;
    Universal.register(&mut registry).map_err(|_| {
        PyValueError::new_err("Couldn't register universal profile, fontspector bug")
    })?;
    GoogleFonts.register(&mut registry).map_err(|_| {
        PyValueError::new_err("Couldn't register Google Fonts profile, fontspector bug")
    })?;
    Fontwerk.register(&mut registry).map_err(|_| {
        PyValueError::new_err("Couldn't register Fontwerk profile, fontspector bug")
    })?;
    Ok(registry.checks.keys().cloned().collect())
}

#[pymodule(name = "fontspector")]
fn fonspector(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CheckTester>()?;
    m.add_function(wrap_pyfunction!(registered_checks, m)?)
}
