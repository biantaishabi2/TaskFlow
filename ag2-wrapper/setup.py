from setuptools import setup, find_packages

setup(
    name="ag2-wrapper",
    version="0.1.3",
    packages=find_packages(include=['ag2_wrapper*']),
    package_dir={'ag2_wrapper': 'ag2_wrapper'},
    package_data={
        'ag2_wrapper': ['**/*.py']
    },
    install_requires=[
        'autogen>=0.2',
        'docker>=6.0'
    ],
    entry_points={},
    python_requires='>=3.8',
    include_package_data=True,
)