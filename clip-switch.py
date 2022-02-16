#!/usr/bin/python3
import os
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError, Element
import argparse
from argparse import RawDescriptionHelpFormatter
from urllib.parse import urlparse


def get_yn(prompt: str) -> str:
    """Get a yes or no response from the user"""

    resp = input(prompt).strip().lower()
    if resp:
        if resp[0] == 'y':
            return True
        elif resp[0] == 'n':
            return False
    return False


def run_replacement(project_xml: Element, replacment_filenames: list[str],
                    replacments_dir: str):
    for clip_el in project_xml.findall('.//track/clipitem'):
        if not clip_el:
            continue
        # Ignore non-video clips
        if clip_el.find('pixelaspectratio') is None:
            continue
        file_el = clip_el.find('file')
        if not file_el:
            continue
        name_element = file_el.find('name')
        fileurl_element = file_el.find('pathurl')
        if not fileurl_element or not fileurl_element.text:
            print('File element malformed')
            exit(1)
        fileurl = fileurl_element.text

        name = name_element.text
        if not name:
            print('Clip name is missing, skipping')
            continue

        candidate = choose_replacement(name, replacment_filenames)
        if not candidate:
            print(f'No replacement found for {name}')
            continue

        url = urlparse(fileurl)

        if not get_yn(f'Replace {name} with {candidate}?'):
            print('Skipping')
            continue

        fullpath = os.path.realpath(os.path.join(replacments_dir, candidate))
        # Update clip name if needed
        clip_name_el = clip_el.find('name')
        if clip_name_el.text == name_element.text:
            clip_name_el.name = candidate
        # Update the file/name element
        name_element.text = candidate
        if not os.path.isfile(fullpath):
            print(f'Somehow I created a bad filepath, \'{fullpath}\' should \
                    exist but does\'t')
            exit(1)
        # Update the file/pathurl element
        fileurl_element.text = url.scheme + '://' + fullpath
    return project_xml


def choose_replacement(current_name: str, choices: list[str]) -> str:
    """
    Choose a replacement from the choi
    """
    for choice in choices:
        # Everything is in the same dir
        if choice == current_name:
            continue
        name, ext = os.path.splitext(choice)
        choice_dir, choice_name = os.path.split(name)
        if current_name.lower().startswith(choice_name.lower()):
            return choice
    # TODO: Get user feedback about lack of choice?


def write_updated_file(xml: Element, output_filename: str):
    with open(output_filename, 'wb') as output_file:
        output_file.write('<?xml version="1.0" encoding="UTF-8"?>\n \
                <!DOCTYPE xmeml>'.encode('UTF-8'))
        xml.write(output_file)


def main():
    parser = argparse.ArgumentParser(
        description="""Reads a Final Cut Pro XML formatted project file and \
switches out existing clips with those found in the provided directory.

Replacements are matched by prefix, case and extension are ignored.

Example:

'PetroPics-873123292.mov' would replace 'petropics-873123292-640_adpp.mp4' \
because they share the prefix 'petropics-873123292'""",
        formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('--finals-dir', required=True)
    parser.add_argument('--output', type=str, help='File name for output file')
    parser.add_argument('project',
                        help='Final Cut Pro XML format project file')
    args = parser.parse_args()

    project_file = os.path.realpath(args.project)
    replacments_dir = args.finals_dir
    if not os.path.isfile(project_file):
        print(f'Cannot find project file {project_file}')
        exit(1)
    replacment_filenames = os.listdir(replacments_dir)
    if not len(replacment_filenames):
        print(f'No final files found in {replacments_dir}')
        exit(1)
    print(f'Opening project: {project_file}')
    try:
        root = ET.parse(project_file)
    except ParseError as pe:
        print(f'Invalid project file: {pe.msg}')
        exit(1)

    root = run_replacement(root, replacment_filenames, replacments_dir)

    if args.output:
        output_filename = args.output
    else:
        output_name, ext = os.path.splitext(project_file)
        output_filename + '_replaced' + ext

    write_updated_file(root, output_filename)


if __name__ == '__main__':
    main()
