# msm - Magazine Subscription Manager

A simple yet powerful tool to manage magazine subscribers, written in Python 3 and using GObject Introspection (Gtk+ 3).

![MSM logo](data/images/msm_logo.png)

## How to install

### Prerequisites

MSM currently needs a couple of dependencies:
- Gtk+ 3 and [`python-gobject`](https://wiki.gnome.org/action/show/Projects/PyGObject)
- [`python-sqlalchemy`](http://www.sqlalchemy.org/)
- [`python-dateutil`](https://labix.org/python-dateutil)

We currently also need [`python-pytz`](http://pytz.sourceforge.net/) at the moment, but we'll replace it with [`python-babel`](http://babel.pocoo.org/) soon (we only need `pytz` for getting country names by ISO 3661-1alpha2 codes).

On windows, you'll also need [`pywin32`](sourceforge.net/projects/pywin32/).

### Installation

Clone the git repository:

```bash
git clone https://github.com/Holzhaus/msm.git
```

Now you can run `msm.pyw`:
```bash
cd msm
chmod +x msm.pyw
./msm.pyw
```

## First Steps

On first start, MSM will create a config directory and the database by itself.

Now you should edit the Magazines. Open the application menu of MSM and click on *Preferences*. In the tab *Magazines* you can add a new magazine and then add possible subscription types to it. If you're done, click *Apply*.

You can now start adding customers.
