from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="zinye_ng",
    version="0.1.0",
    description="Nigeria compliance for Zinye: PAYE, Pension, VAT, WHT, FIRS ATRS, FIRSMBS e-invoicing, NDPR",
    author="Zinye",
    author_email="dev@zinye.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
