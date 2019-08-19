# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""A module containing helpers for dashboard."""

from typing import List, Dict


def generate_html_table_from_dict(dictionary: Dict[str, List[str]], title="") -> str:
    """
    Generate a html table from a dictionary.

    :param dictionary: the dictionary
    :param title: the title
    :return: a html string
    """
    style_tag = "<style>table, th, td{border: 1px solid black;padding:10px;}</style>"
    html_head = "<head>{}</head>".format(style_tag)
    title_tag = "<h2>{}</h2>".format(title) if title else ""

    table_head = "<tr><th>{}</th></tr>".format("</th><th>".join(dictionary.keys()))
    table_body = ""
    for row in zip(*dictionary.values()):
        table_row = "<tr><td>" + "</td><td>".join(row) + "</td></tr>"
        table_body += table_row

    table = "<table>{}{}</table>".format(table_head, table_body)

    html_table = "<html>" + html_head + title_tag + table + "</html>"

    return html_table


def escape_html(string: str, quote=True) -> str:
    """
    Replace special characters "&", "<" and ">" to HTML-safe sequences.

    :param string: the string
    :param quote: If the optional flag quote is true (the default), the quotation mark characters, both double quote (") and single quote (') characters are also translated.

    :return: the escaped string
    """
    string = string.replace("&", "&amp;")  # Must be done first!
    string = string.replace("<", "&lt;")
    string = string.replace(">", "&gt;")
    if quote:
        string = string.replace('"', "&quot;")
        string = string.replace('\'', "&#x27;")
    return string
