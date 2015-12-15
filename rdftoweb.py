""" rdftoweb.py
    author: Bryce Mecum (mecum@nceas.ucsb.edu)

    Cnverts an RDF graph (in Turtle format) into a set of static HTML pags.
"""

import os
import RDF
from urlparse import urlparse
import urllib


def getConcept(uri):
    """
    Return the concept a URI is for, based upon string matching.
    """

    if uri.startswith("https://cn.dataone.org/cn/v1/resolve/"):
        return 'dataset'
    elif uri.startswith("https://dataone.org/person/"):
        return 'person'
    elif uri.startswith("https://dataone.org/organization"):
        return 'organization'
    else:
        return None


def isInternal(pages, uri):
    """
    Checks if a URI is internal or external.

    A URI is internal if that URI is the subject
    of any triples in the graph.
    Otherwise it is external.
    """

    for concept in pages:
        if uri in pages[concept]:
            return True

    return False


def getLinkFor(uri):
    """
    Create a link for a given URI.

    This helps us create links to files that need to be escaped.
    The filename will be singly-quoted and the link will need to be
    doubly-quoted.
    """

    concept = getConcept(uri)
    filename = getFilename(uri)

    link = "/%s/%s.html" % (concept, urllib.quote_plus(filename))

    return link


def getFilename(uri):
    """
    Get the name on disk for a URI.
    """

    filename = None

    if uri.startswith("https://cn.dataone.org/cn/v1/resolve/"):
        filename = uri.replace("https://cn.dataone.org/cn/v1/resolve/", "")
    elif uri.startswith("https://dataone.org/person/"):
        filename = uri.replace("https://dataone.org/person/", "")
    elif uri.startswith("https://dataone.org/organization"):
        filename = uri.replace("https://dataone.org/organization/", "")
    else:
        filename = uri

    filename = urllib.quote_plus(filename)

    return filename


def pageHTML(content=''):
    """
    Creates HTML for a web page and inserts the HTML from content into it.
    """

    css = """body {
                font-family: Sans-serif;
            }

            table {
                border-collapse: true;
            }

            table td {
                padding: 0.25em;
                border: 1px solid black;
            }

            a {
                color: blue;
                text-decoration: none;
            }

            a:visited {
                color: blue;
            }

            a.internal {
                color: green;
            }

            a.internal::before {
                font-family: monospace;
                content: '[INT]'
            }

            a.external {
                color: red;
            }

            a.external::before {
                font-family: monospace;
                content: '[EXT]'
            }"""

    html_string = """<html>
    <head>
        <style type='text/css'>
            %s
        </style>
    </head>
    <body>
        <h1>RDF to Web Output</h1>
        <h2>Concepts</h2>
        <ul class='nav'>""" % css

    for concept in ['person', 'organization', 'dataset']:
        html_string += """
            <li><a href='/%s'>%s</a></li>""" % (concept, concept.capitalize())

    html_string += """
        </ul>"""
    html_string += content
    html_string += """
    </body>
</html>"""

    return html_string


def createIndex(base_dir, pages):
    """
    Create an index HTML for all concepts. The index.html file will located in
    the base directory.
    """

    page_html = pageHTML()

    with open("%s/index.html" % base_dir, 'wb') as f:
        f.write(page_html)


def createConceptIndex(base_dir, pages, concept):
    """
    Create an index HTML page for a concept.
    """

    unique_uris = []

    for page in pages[concept]:
        if page not in unique_uris:
            unique_uris.append(page)

    html_string = """
        <h2>%s</h2>""" % concept.capitalize()

    html_string += """
        <ul>"""

    if not os.path.exists(base_dir + '/' + concept):
        os.mkdir(base_dir + '/' + concept)

    for uri in unique_uris:
        html_string += """
            <li><a href='%s'>%s</a></li>""" % (getLinkFor(uri), uri)

    html_string += """
        </ul>"""

    page_html = pageHTML(html_string)

    with open("%s/%s/index.html" % (base_dir, concept), "wb") as f:
        f.write(page_html)


def createPages(base_dir, pages):
    """
    Create HTML pages for a set of pages.
    """

    for concept in pages:
        concept_folder_path = base_dir + '/' + concept

        if not os.path.exists(concept_folder_path):
            os.mkdir(concept_folder_path)

        # Create indicies
        createIndex(base_dir, pages)
        createConceptIndex(base_dir, pages, concept)

        # Create pages
        for page in pages[concept]:
            content = contentHTML(pages, concept, page)
            page_html = pageHTML(content)

            concept = getConcept(page)
            filename = getFilename(page)

            with open(base_dir + '/' + concept + '/' + filename + ".html", "wb") as f:
                f.write(page_html)


def contentHTML(pages, concept, page):
    """
    Makes the content HTML (what changes across pages) for a page..
    """

    title_html = """<h2><a href='%s'>%s</a></h2>
    """ % (getLinkFor(page), urllib.unquote(page))

    html_string = """%s
        <table>
            <thead>
                <tr>
                    <th>Predicate</th>
                    <th>Object</th>
                </tr>
            </thead>
            <tbody>""" % title_html

    for thing in pages[concept][page]:
        predicate_ele = thing['p']

        # Process object (link internal or not)
        object_string = urllib.unquote(thing['o'])

        is_internal = isInternal(pages, object_string)

        if is_internal:
            thing_filepath = getFilename(object_string)
            object_ele = "<a class='internal' href='%s'>%s</a>" % (getLinkFor(object_string), object_string)

        else:
            if object_string.startswith("http"):
                thing_uri = urllib.unquote(object_string)
                object_ele = "<a class='external' href='%s'>%s</a>" % (thing_uri, thing_uri)
            else:
                object_ele = object_string

        html_string += """
                <tr>
                    <td>%s</td>
                    <td>%s</td>
                </tr>""" % (predicate_ele, object_ele)

    html_string += """
            </tbody>
        </table>"""

    return html_string


def main():
    base_vocab = "http://schema.geolink.org/dev/view/"
    pages = {}
    base_dir = "output"

    parser = RDF.TurtleParser()
    model = RDF.Model()
    parser.parse_into_model(model, "file:./dataset.ttl")

    for statement in model:
        page = None

        if statement.subject.is_resource():
            subject_uri_string = urllib.unquote(str(statement.subject.uri))
            concept = getConcept(subject_uri_string)

            if concept not in pages:
                pages[concept] = {}

            if subject_uri_string not in pages[concept]:
                pages[concept][subject_uri_string] = []
        else:
            # raise Exception("All subjects should be resources.")
            print "Not implemented: skipping statement %s" % statement
            continue


        predicate_string = str(statement.predicate)
        predicate_string = predicate_string.replace(base_vocab, 'glview:')
        pages[concept][subject_uri_string].append({'p': predicate_string, 'o': str(statement.object) })

    # Create base dir
    if not os.path.exists(base_dir):
        os.mkdir(base_dir)
        
    createPages(base_dir, pages)


if __name__ == "__main__":
    main()
