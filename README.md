# py_basic_roguelike

Basic "boilerplate" project for a roguelike, made following [this tutorial](http://www.rogueliketutorials.com/tutorials/tcod/v2/) from rogueliketutorials.com.

Made in python 3.8, using [venv](https://docs.python.org/3/library/venv.html) for dependencies (see `requirements.txt`).

To install:
* `python3 -m venv env`
* `source env/bin/activate`
* `pip install -r requirements.txt`

To start:
* `source /env/bin/activate`
* `python3 main.py`

Basic commands:
* **Arrow keys**: move (bumping into enemies will attack them)
* **mouse hover over entity**: show entity's name
* `i`: open inventory (then, `a-z` to consume/equip item)
* `c`: open character screen
* `Esc`: close window / save and exit
