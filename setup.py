import os

from setuptools import setup


def readme():
    readme_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.md")

    with open(readme_path, encoding="utf-8") as f:
        return f.read()


setup(
    name="smalld",
    description="A minimalist python client for the Discord API",
    long_description=readme(),
    long_description_content_type="text/markdown",
    packages=["smalld", "smalld.resources"],
    package_data={"smalld.resources": ["*"]},
    use_scm_version=True,
    install_requires=[
        "attrdict>=2.0.1",
        "requests>=2.23.0",
        "websocket_client>=0.57.0",
    ],
    setup_requires=["setuptools-scm==3.3.3"],
)
