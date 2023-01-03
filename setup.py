from setuptools import setup
  
setup(
    name='davinci_override',
    version='0.1',
    description='Override for XYZ DaVinci EEPROM',
    author='Ryan Draves',
    author_email='no@nope.com',
    packages=['davinci_override'],
    install_requires=[
        'RPi.GPIO',
    ],
)
