from setuptools import setup

setup(
    name="smalld",
    packages=["smalld"],
    use_scm_version=True,
    install_requires=[
        "attrdict>=2.0.1",
        "requests>=2.23.0",
        "websocket_client>=0.57.0",
    ],
    setup_requires=["setuptools-scm==3.3.3"],
)
