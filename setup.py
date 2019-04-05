from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='smartblinds_client',
    version='0.5',
    description='Unofficial client for the MySmartBlinds Smart Bridge',
    long_description=readme(),
    url='http://github.com/ianlevesque/smartblinds-client',
    author='Ian Levesque',
    author_email='ian@ianlevesque.org',
    packages=['smartblinds_client'],
    install_requires=['auth0-python', 'requests'],
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    zip_safe=False)
