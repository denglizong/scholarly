from .publication import Publication
import re
import pprint
import inspect


_CITATIONAUTHRE = r'user=([\w-]*)'
_HOST = 'https://scholar.google.com{0}'
_PAGESIZE = 100
_EMAILAUTHORRE = r'Verified email at '
_CITATIONAUTH = '/citations?hl=en&user={0}'


class Author:
    """Returns an object for a single author"""

    def __init__(self, nav, authorid, __data):
        self.__nav = nav
        self._filled = set()
        self._sections = {'basics',
                          'indices',
                          'counts',
                          'coauthors',
                          'publications'}

        if isinstance(__data, str):
            self.id = __data
        else:
            self.id = re.findall(_CITATIONAUTHRE, __data('a')[0]['href'])[0]

            pic = '/citations?view_op=medium_photo&user={}'.format(self.id)
            self.url_picture = _HOST.format(pic)

            name_class = self._find_tag_class_name(__data, 'h3', 'name')
            self.name = __data.find('h3', class_=name_class).text

            aff_class = self._find_tag_class_name(__data, 'div', 'aff')
            affiliation = __data.find('div', class_=aff_class)
            if affiliation:
                self.affiliation = affiliation.text

            email_class = self._find_tag_class_name(__data, 'div', 'eml')
            email = __data.find('div', class_=email_class)
            if email:
                self.email = re.sub(_EMAILAUTHORRE, r'@', email.text)

            int_class = self._find_tag_class_name(__data, 'a', 'one_int')
            interests = __data.find_all('a', class_=int_class)
            self.interests = [i.text.strip() for i in interests]

            citedby_class = self._find_tag_class_name(__data, 'div', 'cby')
            citedby = __data.find('div', class_=citedby_class)
            if citedby and citedby.text != '':
                self.citedby = int(citedby.text[9:])

    def _find_tag_class_name(self, __data, tag, text):
        elements = __data.find_all(tag)
        for element in elements:
            if 'class' in element.attrs and text in element.attrs['class'][0]:
                return element.attrs['class'][0]

    def _fill_basics(self, soup):
        self.name = soup.find('div', id='gsc_prf_in').text
        self.affiliation = soup.find('div', class_='gsc_prf_il').text
        self.interests = [i.text.strip() for i in
                          soup.find_all('a', class_='gsc_prf_inta')]

    def _fill_indices(self, soup):
        index = soup.find_all('td', class_='gsc_rsb_std')
        if index:
            self.citedby = int(index[0].text)
            self.citedby5y = int(index[1].text)
            self.hindex = int(index[2].text)
            self.hindex5y = int(index[3].text)
            self.i10index = int(index[4].text)
            self.i10index5y = int(index[5].text)
        else:
            self.citedby = 0
            self.citedby5y = 0
            self.hindex = 0
            self.hindex5y = 0
            self.i10index = 0
            self.i10index5y = 0

    def _fill_counts(self, soup):
        years = [int(y.text) for y in soup.find_all('span', class_='gsc_g_t')]
        cites = [int(c.text) for c in soup.find_all('span', class_='gsc_g_al')]
        self.cites_per_year = dict(zip(years, cites))

    def _fill_publications(self, soup):
        self.publications = list()
        pubstart = 0
        url_citations = _CITATIONAUTH.format(self.id)

        while True:
            for row in soup.find_all('tr', class_='gsc_a_tr'):
                new_pub = Publication(self.__nav, row, 'citations')
                self.publications.append(new_pub)
            if 'disabled' not in soup.find('button', id='gsc_bpf_more').attrs:
                pubstart += _PAGESIZE
                templ = '{0}&cstart={1}&pagesize={2}'
                url = templ.format(url_citations, pubstart, _PAGESIZE)
                soup = self.__nav._get_soup(url)
            else:
                break

    def _fill_coauthors(self, soup):
        self.coauthors = []
        for row in soup.find_all('div', class_='gsc_rsb_aa'):
            author_url = row.find('a')['href']
            author_id = re.search(r'/citations?user=(.*?)\&', author_url).group(1)
            new_coauthor = Author(self.__nav, author_id)

            coauthor_img = row.find('img', class_='gs_pp_df')['src']
            # coauthor_img = coauthor_img.replace("small_photo", "medium_photo")
            # new_coauthor.url_picture = coauthor_img
            
            new_coauthor.name = row.find(tabindex="-1").text
            new_coauthor.affiliation = row.find(class_="gsc_rsb_a_ext").text
            
            self.coauthors.append(new_coauthor)

    def fill(self, sections: list = []):
        """Populate the Author with information from their profile

        The `sections` argument allows for finer granularity of the profile
        information to be pulled.

        :param sections: Sections of author profile to be filled, defaults to ``[]``.

            * ``basics``: fills name, affiliation, and interests;
            * ``citations``: fills h-index, i10-index, and 5-year analogues;
            * ``counts``: fills number of citations per year;
            * ``coauthors``: fills co-authors;
            * ``publications``: fills publications;
            * ``[]``: fills all of the above
        :type sections: ['basics','citations','counts','coauthors','publications',[]] list, optional
        :returns: The filled object if fill was successfull, False otherwise.
        :rtype: Author or bool

        :Example::

            .. testcode::

                search_query = scholarly.search_author('Steven A Cholewiak')
                author = next(search_query)
                print(author.fill(sections=['basic', 'citation_indices', 'co-authors']))

        :Output::

            .. testoutput::

                {'affiliation': 'Vision Scientist',
                 'citedby': 262,
                 'citedby5y': 186,
                 'coauthors': [{'affiliation': 'Kurt Koffka Professor of Experimental Psychology, University '
                                'of Giessen',
                                'filled': False,
                                'id': 'ruUKktgAAAAJ',
                                'name': 'Roland Fleming'},
                               {'affiliation': 'Professor of Vision Science, UC Berkeley',
                                'filled': False,
                                'id': 'Smr99uEAAAAJ',
                                'name': 'Martin Banks'},
                               ...
                               {'affiliation': 'Professor and Dean, School of Engineering, University of '
                                'California, Merced',
                                'filled': False,
                                'id': 'r6MrFYoAAAAJ',
                                'name': 'Edwin D. Hirleman Jr.'},
                               {'affiliation': 'Vice President of Research, NVIDIA Corporation',
                                'filled': False,
                                'id': 'AE7Xvl0AAAAJ',
                                'name': 'David Luebke'}],
                 'email': '@berkeley.edu',
                 'filled': False,
                 'hindex': 8,
                 'hindex5y': 8,
                 'i10index': 7,
                 'i10index5y': 7,
                 'id': '4bahYMkAAAAJ',
                 'interests': ['Depth Cues',
                               '3D Shape',
                               'Shape from Texture & Shading',
                               'Naive Physics',
                               'Haptics'],
                 'name': 'Steven A. Cholewiak, PhD',
                 'url_picture': 'https://scholar.google.com/citations?view_op=medium_photo&user=4bahYMkAAAAJ'}
        """
        sections = [section.lower() for section in sections]
        url_citations = _CITATIONAUTH.format(self.id)
        url = '{0}&pagesize={1}'.format(url_citations, _PAGESIZE)
        soup = self.__nav._get_soup(url)

        if sections == []:
            for i in self._sections:
                if i not in self._filled:
                    getattr(self, f'_fill_{i}')(soup)
        else:
            for i in sections:
                if i in self._sections and i not in self._filled:
                    getattr(self, f'_fill_{i}')(soup)
                    self._filled.add(i)

        return self

    @property
    def filled(self) -> bool:
        """Returns whether or not the author characteristics are filled

        :getter: True if Author object is filled, False otherwise
        :type: bool
        """
        return self._filled == self._sections

    def _get_public_attrs(self):
        res = {}
        for i in dir(self):
            if not i.startswith("_"):
                att = getattr(self, i)
                if not inspect.ismethod(att):
                    res[i] = att
        return res

    def __str__(self):
        return pprint.pformat(self._get_public_attrs())

    def __repr__(self):
        return pprint.pformat(self._get_public_attrs())
