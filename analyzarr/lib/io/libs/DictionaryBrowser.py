# -*- coding: utf-8 -*-

import types

def fsdict(nodes, value, dic):
    """Populates the dictionary 'dic' in a file system-like
    fashion creating a dictionary of dictionaries from the
    items present in the list 'nodes' and assigning the value
    'value' to the innermost dictionary.

    'dic' will be of the type:
    dic['node1']['node2']['node3']...['nodeN'] = value
    where each node is like a directory that contains other
    directories (nodes) or files (values)
    """
    node = nodes.pop(0)
    if node not in dic:
        dic[node] = {}
    if len(nodes) != 0:
        fsdict(nodes,value, dic[node])
    else:
        dic[node] = value

class DictionaryBrowser(object):
    """A class to comfortably access some parameters as attributes"""

    def __init__(self, dictionary={}, pwd=[], sep='.'):
        super(DictionaryBrowser, self).__init__()
        self.sep = sep
        self.home = dictionary
        self.dic = dictionary
        self.pwd = []
        self.cd(pwd) # update self.dic and self.pwd
        self.oldpwd = self.pwd[:]
        self.load_dictionary(dictionary)


    def load_dictionary(self, dictionary):
        for key, value in dictionary.iteritems():
            if isinstance(value, dict):
                value = DictionaryBrowser(value)
            try:
                self.__setattr__(key.encode('utf-8'), value)
            except:
                print "warning: could not set attribute %s with value:" %key
                print value

    def _get_print_items(self, padding = '', max_len=20):
        """Prints only the attributes that are not methods"""
        string = ''
        eoi = len(self.__dict__)
        j = 0
        for item, value in self.__dict__.iteritems():
            # Mixing unicode with strings can deal to Unicode errors
            # We convert all the unicode values to strings
            if type(value) is unicode:
                value = value.encode('utf-8')
            if type(item) != types.MethodType:
                if isinstance(value, DictionaryBrowser):
                    if j == eoi - 1:
                        symbol = u'└── '
                    else:
                        symbol = u'├── '
                    string += u'%s%s%s\n' % (padding, symbol, item)
                    if j == eoi - 1:
                        extra_padding = u'    '
                    else:
                        extra_padding = u'│   '
                    string += value._get_print_items(padding + extra_padding)
                else:
                    if j == eoi - 1:
                        symbol = u'└── '
                    else:
                        symbol = u'├── '
                    strvalue = str(value)
                    if len(strvalue) > 2 * max_len:
                        right_limit = min(max_len, len(strvalue) - max_len)
                        value = u'%s ... %s' % (strvalue[:max_len],
                                                strvalue[-right_limit:])
                    string += u"%s%s%s = %s\n" % (padding, symbol, item, value)
            j += 1
        return string

    def __repr__(self):
        return self._get_print_items().encode('utf8', errors='ignore')

    def __getitem__(self,key):
        return self.__dict__.__getitem__(key)

    def len(self):
        return len(self.__dict__.keys())

    def keys(self):
        return self.__dict__.keys()

    def as_dictionary(self):
        par_dict = {}
        for item, value in self.__dict__.iteritems():
            if type(item) != types.MethodType:
                if isinstance(value, DictionaryBrowser):
                    value = value.as_dictionary()
                par_dict.__setitem__(item, value)
        return par_dict

    def has_item(self, item_path):
        """Given a path, return True if it exists

        Parameters
        ----------
        item_path : Str
            A string describing the path with each item separated by a point

        Example
        -------

        >>> dict = {'To' : {'be' : True}}
        >>> dict_browser = DictionaryBrowser(dict)
        >>> dict_browser.has_item('To')
        True
        >>> dict_browser.has_item('To.be')
        True
        >>> dict_browser.has_item('To.be.or')
        False


        """
        if type(item_path) is str:
            item_path = item_path.split('.')
        attrib = item_path.pop(0)
        if hasattr(self, attrib):
            if len(item_path) == 0:
                return True
            else:
                item = self[attrib]
                if isinstance(item, type(self)): 
                    return item.has_item(item_path)
                else:
                    return False
        else:
            return False

    def add_node(self, node_path):
        keys = node_path.split('/')
        current_dict = self.__dict__
        for key in keys:
            if key not in current_dict:
                current_dict[key] = DictionaryBrowser()
            current_dict = current_dict[key].__dict__

    def ls(self, pwd=[], dbg=False):
        """List the contents of the instance's dictionary
        attribute 'dic' given the path in pwd in a *nix-like
        fashion.

        'pwd' can be either a list or a string of keys
        separated by the separator attribute 'sep' (defaults to '.')

        the special keyword pwd='..' lists the contents
        relative to the previous key (directory).

        if 'dbg' is True, useful information is printed on screen

        E.g.
        obj.ls('root.dir1.dir2.dir3')
        obj.ls(['root', 'dir1', 'dir2', 'dir3'])
        """
        pwd = pwd[:] # don't modify the input object, work with a copy

        if pwd == '..':
            dic = DictionaryBrowser(dictionary=self.home, pwd=self.pwd[:-1])
            return dic.ls()

        if type(pwd) is str:
            pwd = pwd.split(self.sep) # turn pwd into a list
        try:
            cdir = pwd.pop(0)   # current directory
        except:
            cdir = ''
        if cdir:
            if pwd:
                try:
                    dic = DictionaryBrowser(dictionary=self.dic[cdir])
                    return dic.ls(pwd)
                except KeyError, key:
                    if dbg:
                        print('Key %s does not exist. Nothing to do.'
                              % str(key))
                    return None
            else:
                try:
                    if type(self.dic[cdir]) is dict:
                        # 'sub-directory' (return content)
                        out = self.dic[cdir].keys()
                        out.sort()
                        return out
                    else:
                        # 'file' (return name (key) and value)
                        return cdir, self.dic[cdir]
                except KeyError, key:
                    if dbg:
                        print('Key %s does not exist. Nothing to do.'
                              % str(key))
                    return None
        else:
            try:
                out = self.dic.keys()
                out.sort()
                return out
            except:
                if dbg:
                    msg = 'An error occurred processing '
                    msg += 'the ls() method of '
                    msg += self.__class__.__name__
                    print(msg)
                return None

    def cd(self, pwd=[], dbg=False):
        """Updates the instance's 'dic' attribute to the
        sub-dictionary given by the path in 'pwd' in a
        *nix-like fashion.

        'dic' should be a dictionary of dictionaries

        'pwd' can be either a list or a string of keys
        separated by the separator attribute 'sep' (defaults to '.')

        'pwd' defaults to [], that is
        cd() brings you to the 'root' dictionary

        the special keyword pwd='..' updates 'dic' to
        the previous key (directory).

        the special keyword pwd='-' updates 'dic' to
        the old key (directory).

        if 'dbg' is True, useful information is printed on screen

        E.g.
        obj.cd('root.dir1.dir2.dir3')
        obj.cd(['root', 'dir1', 'dir2', 'dir3'])
        """

        pwd = pwd[:] # don't modify the input object, work with a copy

        if pwd == '..': # going to previous directory (in *nix: cd ..)
            self.oldpwd = self.pwd[:]
            self.pwd.pop()
            self.dic = self.home.copy()
            pwd = self.pwd[:]
            newdic = DictionaryBrowser(dictionary=self.dic, pwd=pwd, sep=self.sep)
            self.dic = newdic.dic.copy() # update the 'dic' attribute
            self.pwd =  newdic.pwd[:]
        elif pwd == '-': # going to old directory (in *nix: cd -)
            self.dic = self.home.copy()
            pwd = self.oldpwd[:]
            self.oldpwd = self.pwd[:]
            newdic = DictionaryBrowser(dictionary=self.dic, pwd=pwd, sep=self.sep)
            self.dic = newdic.dic.copy() # update the 'dic' attribute
            self.pwd =  newdic.pwd[:]
        else:
            if type(pwd) is str:
                pwd = pwd.split(self.sep) # turn pwd into a list
            try:
                cdir = pwd.pop(0) # current directory
            except:
                cdir = ''
            if cdir:
                try:
                    if type(self.dic[cdir]) is dict:
                        # 'sub-directory' (return content)
                        # print('entering', cdir) # DEBUG
                        self.dic = self.dic[cdir]
                        self.pwd.append(cdir)
                    else:
                        if dbg:
                            msg = 'Key "%s" ' % str(cdir)
                            msg += 'is not a (sub)dictionary.'
                            msg += ' Nothing to do.'
                            print(msg)                                  
                        return None
                    if pwd:
                        newdic = DictionaryBrowser(dictionary=self.dic, pwd=pwd,
                                                   sep=self.sep)
                        self.dic = newdic.dic.copy()
                        self.pwd += newdic.pwd
                except KeyError, key: # non existing key (directory)
                    if dbg:
                        msg = 'Key %s does not exist' % str(key)
                        msg += ' in current (sub)dictionary. Nothing to do.' 
                        print(msg)
                    return None
            else:
                self.dic = self.home.copy()
                self.oldpwd = self.pwd[:]
                self.pwd = []