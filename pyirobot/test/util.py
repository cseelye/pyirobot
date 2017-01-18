#!/usr/bin/env python
#pylint: skip-file

import random
import string

def RandomIP():
    return "{}.{}.{}.{}".format(random.randint(1,254),
                                random.randint(1,254),
                                random.randint(1,254),
                                random.randint(1,254))

def RandomComplexString(length):
    return "".join(random.choice(string.ascii_letters + string.digits + string.punctuation + " ") for i in range(length))