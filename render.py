#!/usr/bin/env python3

import os
import markdown

from frontmatter import Frontmatter
from bin.govukify import govukify_markdown_output
from bin.jinja_setup import env, render
from bin.helpers import read_in_json
from digital_land_frontend.filters import make_link

from markdown.extensions.toc import TocExtension

# register jinja filters
env.filters["make_link"] = make_link

# set variables to make available to all templates
env.globals["staticPath"] = "https://digital-land.github.io"

# init markdown
md = markdown.Markdown(extensions=[TocExtension(toc_depth="2-3")])

def compile_markdown(md, s):
    html = md.convert(s)
    return govukify_markdown_output(html)

# making markdown compiler available to jinja templates
def markdown_filter(s):
    return compile_markdown(md, s)

env.filters["markdown"] = markdown_filter

def get_project_content(filename):
    file_content = Frontmatter.read_file(filename)
    return {
        "name": file_content["attributes"].get("name"),
        "status": file_content["attributes"].get("status"),
        "characteristics": file_content["attributes"].get("characteristics"),
        "frontmatter": file_content["attributes"],
        "description": compile_markdown(md, file_content["body"]),
    }


def markdown_files_only(files, file_ext=".md"):
    return [f for f in files if f.endswith(file_ext)]


# get templates
index_template = env.get_template("index.html")
project_template = env.get_template("project.html")
content_template = env.get_template("content.html")
design_history_template = env.get_template("design-history.html")

project_dir = "projects/"
projects = os.listdir(project_dir)

for project in projects:
    hasMultipleDatasets = False
    project_content = get_project_content(f"{project_dir}{project}/index.md")
    # get dataset content to display on project page
    if os.path.isdir(f"{project_dir}{project}/datasets"):
        datasets = []
        md_files = markdown_files_only(os.listdir(f"{project_dir}{project}/datasets"))

        for f in md_files:
            datasets.append(get_project_content(f"{project_dir}{project}/datasets/{f}"))
        project_content["datasets"] = datasets

    # render any additional content pages
    if os.path.isdir(f"{project_dir}{project}/content"):
        md_files = markdown_files_only(os.listdir(f"{project_dir}{project}/content"))

        design_history = []
        for f in md_files:
            file_content = Frontmatter.read_file(f"{project_dir}{project}/content/{f}")
            html = compile_markdown(md, file_content["body"])
            render(
                f"{project}/{f.replace('.md', '')}/index.html",
                content_template,
                content=html,
                toc=md.toc_tokens,
                fm=file_content["attributes"],
                project=project,
            )

            design_history.append(
                {
                    "name": file_content["attributes"]["name"],
                    "url": f"../{f.replace('.md', '')}",
                }
            )
        # generate a design history page
        render(
            f"{project}/design-history/index.html",
            design_history_template,
            project=project,
            design_history=design_history,
        )

    render(f"{project}/index.html", project_template, project=project_content)


# generate summary for /index page
summary = read_in_json("config/project_buckets.json")
for project in projects:
    filename = f"{project_dir}{project}/index.md"
    if os.path.exists(filename):
        file_content = Frontmatter.read_file(filename)
        summary.setdefault(file_content["attributes"].get("status").lower(), {"projects":[]})
        project_summary = {
            "project_dir": project,
            "name": file_content["attributes"].get("name"),
            "description": file_content["attributes"].get("one-liner"),
        }
        summary[file_content["attributes"].get("status").lower()]["projects"].append(
            project_summary
        )
for k in summary.keys():
    summary[k]["projects"].sort(key=lambda x: x["name"])
# generate index page
render(f"index.html", index_template, projects=summary)