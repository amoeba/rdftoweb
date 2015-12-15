""" rdftoweb.py
    author: Bryce Mecum (mecum@nceas.ucsb.edu)

    Cnverts an RDF graph (in Turtle format) into a set of static HTML pags.
"""

import os
import RDF
import shutil # for copying the styles.css file
from urlparse import urlparse
import urllib


def getConcept(uri):
    """
    Return the concept a URI is for, based upon string matching.
    """

    if uri.startswith("http://lod.dataone.org/dataset"):
        return 'dataset'
    elif uri.startswith("http://lod.dataone.org/person"):
        return 'person'
    elif uri.startswith("http://lod.dataone.org/organization"):
        return 'organization'
    else:
        return 'blank'


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


def pageHTML(content='', concepts=None):
    """
    Creates HTML for a web page and inserts the HTML from content into it.
    """

    html_string = """<html>
    <head>
        <link rel="stylesheet" href="/styles.css">
    </head>
    <body>
        <h1>RDF to Web Output</h1>

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

    for statement in pages[concept][page]:
        # Do something different depending on what the object is
        #   If blank: Inline the node
        #   If URI:
        #       - If it links to an internal resource, show that
        #       - If it links to an exteranl resource, show that
        #   If literal: Just show it

        object_string = statement['o']

        # Check for blank first
        if 'blank' in pages and object_string in pages['blank']:
            object_content = blankNodeHTML(object_string, pages)
        # Internal
        elif isInternal(pages, object_string):
            object_content = "<a class='internal' href='%s'>%s</a>" % (getLinkFor(object_string), substitutePrefix(object_string))

        # External or literal
        else:
            if object_string.startswith("http"):
                object_uri = urllib.unquote(object_string)
                object_content = "<a class='external' href='%s'>%s</a>" % (object_uri, substitutePrefix(object_uri))
            else:
                object_content = object_string

        predicate_ele = substitutePrefix(statement['p'])

        html_string += """
                <tr>
                    <td>%s</td>
                    <td>%s</td>
                </tr>""" % (predicate_ele, object_content)

    html_string += """
            </tbody>
        </table>"""

    return html_string


def blankNodeHTML(blank_node, pages):
    """Generates an HTML table for a blank node for inlining inside a result
    table for another resource."""

    if 'blank' not in pages:
        raise Exception("blankNodeHTML was called but no blank nodes were found.")

    if blank_node not in pages['blank']:
        raise Exception("blankNodeHTML was called for a blank node that doesn't exist.")

    blank_node_content = pages['blank'][blank_node]

    if len(blank_node_content) <= 0:
        raise Exception("Blank node was found but had on statements associated with it.")

    html_string = """<table>
            <thead>
                <tr>
                    <th>Predicate</th>
                    <th>Object</th>
                </tr>
            </thead>
            <tbody>"""

    for statement in blank_node_content:
        predicate_content = statement['p']

        # Prefix the predicate if we can
        predicate_content = substitutePrefix(predicate_content)

        object_string = statement['o']

        # Blank
        if object_string in pages['blank']:
            object_content = blankNodeHTML(object_string, pages)

        # Internal
        elif isInternal(pages, object_string):
            object_content = "<a class='internal' href='%s'>%s</a>" % (getLinkFor(object_string), substitutePrefix(object_string))

        # External or literal
        else:
            if object_string.startswith("http"):
                object_uri = urllib.unquote(object_string)
                object_content = "<a class='external' href='%s'>%s</a>" % (object_uri, substitutePrefix(object_uri))
            else:
                object_content = object_string


        html_string += """<tr>
            <td>
                %s
            </td>
            <td>
                %s
            </td>
        </tr>""" % (predicate_content, object_content)

    html_string += """</tbody>
        </table>"""

    return html_string


def substitutePrefix(term):
    """Attempt to prefix the term with its namespace string instead of the
    fully-specified URI.

    Returns either the prefix'd term string (foo:Bar) or the original string if
    the term did not start with a URI in an known namespace."""

    for prefix in NS:
        if term.startswith(NS[prefix]):
            term = term.replace(NS[prefix], prefix + ":")

    return term


def main():
    base_vocab = "http://schema.geolink.org/dev/view/"
    pages = {}
    base_dir = "output"

    parser = RDF.TurtleParser()
    model = RDF.Model()
    parser.parse_into_model(model, "file:./dataset.ttl")

    for statement in model:
        page = None

        subject = urllib.unquote(str(statement.subject))
        concept = getConcept(subject)

        if concept not in pages:
            pages[concept] = {}

        if subject not in pages[concept]:
            pages[concept][subject] = []

        predicate_string = str(statement.predicate)
        predicate_string = predicate_string.replace(base_vocab, 'glview:')
        pages[concept][subject].append({'p': predicate_string, 'o': str(statement.object) })

    # Create base dir
    if not os.path.exists(base_dir):
        os.mkdir(base_dir)

    createPages(base_dir, pages)

    # Copy in the base stylehseet
    shutil.copyfile('styles.css', 'output/styles.css')


if __name__ == "__main__":
    main()
