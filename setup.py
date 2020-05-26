from setuptools import find_packages, setup

fmt_deps = ["autoflake==1.3.1", "isort==4.3.21", "black==19.3b0"]
setup_deps = ["setuptools-scm==3.3.3"]
test_deps = ["pytest==5.2.1", "pytest-cov==2.8.1"]
extras = {"fmt": fmt_deps, "test": test_deps}

setup(
    name="smalld",
    packages=find_packages(),
    use_scm_version=True,
    install_requires=[
        "attrdict>=2.0.1",
        "requests>=2.23.0",
        "websocket-client>=0.57.0",
    ],
    tests_require=test_deps,
    extras_require=extras,
    setup_requires=setup_deps,
)
