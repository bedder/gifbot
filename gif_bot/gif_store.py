# MIT License
#
# Copyright (c) 2018 Matthew Bedder (matthew@bedder.co.uk)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Implementation of the ``GifStore`` class.
"""

import random
from typing import Text, List, Optional, Dict, Set  # pylint: disable=unused-import


class GifStore:
    """ An storage and accessor class for maintaining a collection of nice, wholesome GIFs """

    class Element:  # pylint: disable=too-few-public-methods
        """ Storage struct for GIF data """
        def __init__(self, url: Text, tags: Set[Text]) -> None:
            self.url = url
            self.tags = tags

    def __init__(self, adjectives: Optional[List[Text]] = None,
                 manifest_data: Optional[Text] = None) -> None:
        self.elements = []  # type: List[GifStore.Element]
        self.tags = {}  # type: Dict[Text, int]
        self.modifiers = adjectives if adjectives is not None else ["wholesome"]

        if manifest_data is not None:
            for line in manifest_data.splitlines():
                line_data = line.split(",")
                if len(line_data) >= 2:
                    self.add_gif(line_data[0], set(line_data[1:]))

    def add_gif(self, url: Text, tags: Set[Text]) -> None:
        """
        Adds a GIF into the store
        :param url: The URL of the new GIF
        :param tags: The tags for the new GIF
        """
        existing_elements = [element for element in self.elements if element.url == url]
        if existing_elements:
            # Add any new tags
            for tag in tags.difference(existing_elements[0].tags):
                self.tags[tag] = 1

            # Add the new tags to the existing record
            existing_elements[0].tags.update(tags)
        else:
            # Add a new record
            self.elements.append(self.Element(url, tags))
            for tag in tags:
                if tag in self.tags.keys():
                    self.tags[tag] += 1
                else:
                    self.tags[tag] = 1

    def remove_gif(self, url: Text) -> None:
        """
        Removes a GIF from the store
        :param url: The URL of the GIF we want to remove
        """
        matches = [e for e in self.elements
                   if e.url == url]
        if not matches:
            return
        self.elements = [e for e in self.elements if e.url != url]
        # Update the tags
        match_tags = [t for t_ in matches
                      for t in t_.tags]
        for tag in match_tags:
            self.tags[tag] -= 1
            if self.tags[tag] == 0:
                del self.tags[tag]

    def get_tags(self) -> Set[Text]:
        """
        Gets all of the tags in the store
        """
        return {tag for tag in self.tags}

    def get_info(self, max_tags: int) -> Text:
        """
        Gets the status of the store
        :param max_tags: The maximum number of tags to return
        """
        text = "We have " + str(len(self.elements)) + " gifs, including..."
        if max == 0 or len(self.tags) < max_tags:
            for tag in self.tags:
                count = self.tags[tag]
                text += "\n  " + str(count) + \
                        " " + random.choice(self.modifiers) + \
                        " " + tag + \
                        " gif" + ("s" if count > 1 else "") + "!"
        else:
            for tag in random.sample(list(self.tags), max_tags):
                count = self.tags[tag]
                text += "\n  " + str(count) + \
                        " " + random.choice(self.modifiers) + \
                        " " + tag + \
                        " gif" + ("s" if count > 1 else "") + "!"
            text += "\n... and many more!"
        return text

    def get_count(self, tag: Text) -> int:
        """
        Gets the number of GIFs containing the provided tag(s)
        :param tag: A tag, or multiple tags joined with "+"  (e.g. `"cat+dog`")
        """
        sub_tags = tag.split("+")
        return len([e for e in self.elements if all(t in e.tags for t in sub_tags)])

    def get_gif(self, tag: Text) -> Optional[Text]:
        """
        Gets a GIF of the provided type
        :param tag: A tag, or multiple tags joined with "+"  (e.g. `"cat+dog`")
        :return: Either a URL if a GIF of the provided type exists in the store, else None
        """
        if tag == "all":
            matches = self.elements
        else:
            sub_tags = tag.split("+")
            matches = [e for e in self.elements if all(t in e.tags for t in sub_tags)]
        return random.choice(matches).url if matches else None

    def save_manifest(self, filename: Text) -> None:
        """
        Saves the current status of the store into the manifest file
        :param filename: The name we should save the manifest file as
        """
        file = open(filename, "w")
        for element in self.elements:
            line = element.url
            for tag in element.tags:
                line += "," + tag
            file.write(line + "\n")
        file.close()
