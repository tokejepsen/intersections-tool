import app


show = app.show
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0

version_info = (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)
version = "{0}.{1}.{2}".format(*version_info)
__version__ = version

__all__ = ["version", "version_info", "__version__"]
