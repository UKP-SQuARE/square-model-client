from setuptools import setup, find_packages

__version__ = "0.0.1"

setup(
    name="square_model_client",
    version=__version__,
    license="MIT",
    description="",
    url="https://github.com/UKP-SQuARE/square-model-client",
    download_url=f"https://github.com/UKP-SQuARE/square-model-client/archive/refs/tags/v{__version__}.tar.gz",
    author="UKP",
    author_email="baumgaertner@ukp.informatik.tu-darmstadt.de",
    packages=find_packages(
        exclude=(
            "Makefile",
            ".gitignore",
            "requirements.dev.txt",
            ".pre-commit-config.yaml",
        )
    ),
    install_requires=["aiohttp>=3.8.3", "numpy>=1.23.4", "square-auth==0.0.11"],
)
