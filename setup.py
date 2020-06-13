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
    url="https://github.com/princesslana/smalld.py",
    author="Princess Lana",
    author_email="ianagbip1oti@gmail.com",
    license="MIT",
    packages=["smalld", "smalld.resources"],
    package_data={"smalld.resources": ["*"]},
    use_scm_version=True,
    install_requires=[
        "attrdict>=2.0.1",
        "requests>=2.23.0",
        "websocket_client>=0.57.0",
    ],
    setup_requires=["setuptools-scm==3.3.3"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
