# rdftoweb

Note: Only tested on my own Turtle files.

The script `rdftoweb.py` converts an RDF graph (in Turtle format only for now) into a set of static HTML pages.
Just run `rdftoweb.py myturtlefile.ttl` and a folder named `output` should be created in the working directory.
Then just load the HTML in a web server of some sort like [devd](https://github.com/cortesi/devd).
