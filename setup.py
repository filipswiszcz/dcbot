from setuptools import setup

with open("README.md") as f:
    readme = f.read()

setup(
    name="sirius",
    version="0.0.2",
    description="Discord bot.",
    long_description=readme,
    author="Filip Świszcz"
)