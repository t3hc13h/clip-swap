#!/usr/bin/python3
import os
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError, Element
import argparse
from argparse import RawDescriptionHelpFormatter
from urllib.parse import urlparse
from typing import List
import logging
import gzip

def get_yn(prompt: str) -> bool:
    """Get a yes or no response from the user"""

    resp = input(prompt).strip().lower()
    if resp:
        if resp[0] == 'y':
            return True
        elif resp[0] == 'n':
            return False
    return False


def run_prempro_replacement(project_xml: Element, replacement_filenames: List[str],
                            replacements_dir: str,
                            project_path: str):
    """Main Final Cut Pro replacement loop"""
    for media_el in project_xml.findall('./Media'):
        title_el = media_el.find('Title')
        if title_el is None:
            logging.info(f'Media element {media_el} has no title, skipping')
            continue

        name = title_el.text
        candidate = choose_replacement(name, replacement_filenames)
        if not candidate:
            logging.debug(f'No replacement found for {name}, skipping')
            continue
        logging.debug(f'Replacing {name} with {candidate}')
        title_el.text = candidate
        fullpath = os.path.realpath(os.path.join(replacements_dir, candidate))
        candidate_rel_path = os.path.relpath(fullpath, project_path)
        logging.debug(f'Replacement full path {fullpath}')
        logging.debug(f'Replacement relative path {candidate_rel_path}')

        file_path_el = media_el.find('FilePath')
        if file_path_el is None:
            logging.debug(f'FilePath element not found, skipping')
            continue
        file_path_el.text = fullpath

        rel_path_el = media_el.find('RelativePath')
        if rel_path_el is None:
            logging.debug(f'RelativePath element not found, skipping')
            continue
        rel_path_el.text = candidate_rel_path

        actual_file_path_el = media_el.find('ActualMediaFilePath')
        if actual_file_path_el is None:
            logging.debug(f'ActualMediaFilePath element not found, skipping')
            continue
        actual_file_path_el.text = fullpath

        for clip_project_name_el in project_xml.findall(f".//ClipProjectItem/ProjectItem/Name"):
            if clip_project_name_el.text == name:
                logging.debug(f'Updating ProjectItem/Name = {name} with {candidate}')
                clip_project_name_el.text = candidate

        for master_clip_name_el in project_xml.findall(f".//MasterClip/Name"):
            if master_clip_name_el.text == name:
                logging.debug(f'Updating MasterClip/Name = {name} with {candidate}')
                master_clip_name_el.text = candidate

        for clip_logging_info_el in project_xml.findall(f".//ClipLoggingInfo/ClipName"):
            if clip_logging_info_el.text == name:
                logging.info(f'Updating ClipName = {name} with {candidate}')
                clip_logging_info_el.text = candidate

        for sub_clip_el in project_xml.findall(f".//SubClip/Name"):
            if sub_clip_el.text == name:
                logging.info(f'Updating SubClip/Name = {name} with {candidate}')
                sub_clip_el.text = candidate

    return project_xml


def run_fcp_replacement(project_xml: Element, replacement_filenames: List[str],
                        replacements_dir: str):
    """Main Final Cut Pro replacement loop"""

    for clip_el in project_xml.findall('.//track/clipitem'):
        if not clip_el:
            continue
        # Ignore non-video clips
        if clip_el.find('pixelaspectratio') is None:
            continue
        file_el = clip_el.find('file')
        if file_el is None:
            continue
        name_element = file_el.find('name')
        fileurl_element = file_el.find('pathurl')
        if fileurl_element is None or not fileurl_element.text:
            logging.error(f'File element malformed')
            exit(1)
        fileurl = fileurl_element.text

        name = name_element.text
        if not name:
            logging.info('Clip name is missing, skipping')
            continue

        candidate = choose_replacement(name, replacement_filenames)
        if not candidate:
            logging.info(f'No replacement found for {name}')
            continue

        url = urlparse(fileurl)

        if not get_yn(f'Replace {name} with {candidate}?: '):
            logging.info('Skipping')
            continue
        # Assuming we won't want to update multiple
        # clips with the same file
        replacement_filenames.remove(candidate)
        fullpath = os.path.realpath(os.path.join(replacements_dir, candidate))
        # Update clip name if needed
        clip_name_el = clip_el.find('name')
        if clip_name_el.text == name_element.text:
            clip_name_el.text = candidate
        # Update the file/name element
        name_element.text = candidate
        if not os.path.isfile(fullpath):
            logging.error(f'Somehow I created a bad filepath, \'{fullpath}\' should \
                    exist but doesn\'t')
            exit(1)
        # Update the file/pathurl element.
        # Replace the url path to maintain the scheme and host
        fileurl_element.text = url._replace(path=fullpath).geturl()
    return project_xml


def choose_replacement(current_name: str, choices: List[str]) -> str:
    """Choose a replacement from choices list"""

    for choice in choices:
        # Everything is in the same dir
        if choice == current_name:
            continue
        name, ext = os.path.splitext(choice)
        choice_dir, choice_name = os.path.split(name)
        if current_name.lower().startswith(choice_name.lower()):
            return choice


def write_prproj_file(xml: Element, output_filename: str, compressed: bool):
    """Write the updated Premiere Pro XML to the output file"""
    _open = gzip.open if compressed else open
    with _open(output_filename, 'wb') as output_file:
        output_file.write('<?xml version="1.0" encoding="UTF-8" ?>\n'.encode('UTF-8'))
        xml.write(output_file)


def write_fcp_file(xml: Element, output_filename: str, compressed: bool):
    """Write the update Final Cut Pro XML to the output file"""
    with open(output_filename, 'wb') as output_file:
        output_file.write('<?xml version="1.0" encoding="UTF-8"?>\n \
                <!DOCTYPE xmeml>\n'.encode('UTF-8'))
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
    parser.add_argument('--log', type=str, help='Log level')
    parser.add_argument('project',
                        help='Final Cut Pro XML format project file')
    args = parser.parse_args()
    loglevel = args.log
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(format='%(message)s', encoding='utf-8', level=numeric_level)

    project_file = os.path.realpath(args.project)
    replacments_dir = os.path.realpath(args.finals_dir)
    if not os.path.isfile(project_file):
        print(f'Cannot find project file {project_file}')
        exit(1)
    if not os.path.isdir(replacments_dir):
        print(f'Finals directory {replacments_dir} not found')
        exit(1)
    replacement_filenames = os.listdir(replacments_dir)
    if not len(replacement_filenames):
        print(f'No final files found in {replacments_dir}')
        exit(1)
    print(f'Opening project: {project_file}')
    try:
        project_file_obj = gzip.open(project_file)
        # Need to read something to test the file
        project_file_obj.peek(1)
        compressed = True
    except gzip.BadGzipFile:
        # Woops, not zipped just try reading it
        project_file_obj = open(project_file)
        compressed = False
    try:
        project_tree = ET.parse(project_file_obj)
    except ParseError as pe:
        print(f'Invalid project file: {pe.msg}')
        exit(1)
    finally:
        if project_file_obj:
            project_file_obj.close()

    if args.output:
        output_filename = args.output
    else:
        output_name, ext = os.path.splitext(project_file)
        output_filename = output_name + '_replaced' + ext

    if os.path.isfile(output_filename):
        if not get_yn("Output file already exists. Overwrite?: "):
            exit(1)

    root = project_tree.getroot()
    logging.info(f'Writing updated file: {output_filename}')
    if root.tag == 'PremiereData':
        run_prempro_replacement(root, replacement_filenames, replacments_dir,
                                os.path.dirname(project_file))
        write_prproj_file(project_tree, output_filename, compressed)
    elif root.tag == 'xmeml':
        run_fcp_replacement(root, replacement_filenames, replacments_dir)
        write_fcp_file(project_tree, output_filename)
    else:
        print('Unrecognized file format :(')



if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
