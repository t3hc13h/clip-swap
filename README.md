#### What is this thing

A small utility to replace clips in a Final Cut Pro XML.

#### Install

Nothing fancy, just put it where ya like and make it executable.

```shell
curl -O https://github.com/t3hc13h/clip-swap/blob/7deef4123152055e33d46bc018c731d5b0ff0337/clip-switch.py
chmod +x ./clip-switch.py
```

#### Usage
```shell
$ ./clip-swap.py --help
usage: clip-switch.py [-h] --finals-dir FINALS_DIR [--output OUTPUT] project

Reads a Final Cut Pro XML formatted project file and switches out existing clips with those found in the provided directory.

Replacements are matched by prefix, case and extension are ignored.

Example:

'PetroPics-873123292.mov' would replace 'petropics-873123292-640_adpp.mp4' because they share the prefix 'petropics-873123292'

positional arguments:
  project               Final Cut Pro XML format project file

optional arguments:
  -h, --help            show this help message and exit
  --finals-dir FINALS_DIR
  --output OUTPUT       File name for output file
```
