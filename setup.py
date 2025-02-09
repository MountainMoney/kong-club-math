from setuptools import setup, find_packages
import sys 
import os 

cwd = os.path.dirname(os.path.abspath(__file__))
if cwd not in sys.path:
    sys.path.append(cwd)


setup(
    name='zuck-engine',
    version='1.0.0',
    python_requires=">=3.12,<3.13",
    author="CarrotTeam",
    packages=find_packages()
)