#!/usr/bin/python3
import os
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
import argparse
from argparse import RawDescriptionHelpFormatter

from urllib.parse import urlparse


# Don't actually have a use for this
def calc_lev_distance(s1, s2) -> int:
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2 + 1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1],
                                           distances_[-1])))
        distances = distances_
    return distances[-1]


def get_yn(prompt: str) -> str:
    resp = input(prompt).strip().lower()
    if resp:
        if resp[0] == 'y':
            return True
        elif resp[0] == 'n':
            return False
    return False


def run_replacement(project_file: str, replacment_filenames: list[str],
                    replacments_dir: str):
    try:
        root = ET.parse(project_file)
    except ParseError as e:
        print('Invalid project file')
        exit(1)
    for clip_el in root.findall('.//track/clipitem'):
        if not clip_el:
            continue
        # Ignore non-video clips
        if clip_el.find('pixelaspectratio') is None:
            continue
        e = clip_el.find('file')
        if not e:
            continue
        name_element = e.find('name')
        candidate = choose_replacement(name_element.text, replacment_filenames)
        fileurl_element = e.find('pathurl')
        fileurl = fileurl_element.text
        name = name_element.text
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
        name_element.text = candidate
        if not os.path.isfile(fullpath):
            print(f'Somehow I created a bad filepath, \'{fullpath}\' should \
                    exist but does\'t')
            exit(1)
        fileurl_element.text = url.scheme + '://' + fullpath
    return root


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


def main():
    parser = argparse.ArgumentParser(
        description="""Switch out existing clip files with files with matching \
files from the provided directory.

Replacements are matched by prefix, case and extension are ignored.

Example:

PetroPics-873123292.mov would replace petropics-873123292-640_adpp.mp4

because they share the prefix 'petropics-873123292'""",
        formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('--finals-dir', required=True)
    parser.add_argument('project')
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
    root = run_replacement(project_file, replacment_filenames, replacments_dir)
    output_name, ext = os.path.splitext(project_file)
    with open(output_name + '_replaced' + ext, 'wb') as output_file:
        output_file.write('<?xml version="1.0" encoding="UTF-8"?>\n \
                <!DOCTYPE xmeml>'.encode('UTF-8'))
        root.write(output_file)


if __name__ == '__main__':
    main()
