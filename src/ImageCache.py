class ImageCache:
    
    """a cache for Tk image objects and their python wrappers

    The current goal of this cache is to provide a safe mechanism for
    sharing image objects between multiple Viewer windows.

    In future release, the image cache should actually delete objects
    from the cache (what a concept!). Currently, a Grail process will
    grow without bound as new images are displayed. This is a bug.
    """

    def __init__(self, url_cache):
        self.image_objects = {}
        self.old_objects = {}
        self.current_owners = {}
        self.url_cache = url_cache

    def debug_show_state(self):
        print "debugging ouput\ncurrent state of image cache"
        for image in self.image_objects.keys():
            print "Image: %s.\n  Owners=%s" % (image,
                                            self.current_owners[image])
        for owner, images in self.old_objects.items():
            print "Old images owned by ", owner
            for image in images:
                print image

    def form_key(self, (url, width, height)):
        if url:
            return (self.url_cache.url2key(url, "GET", {}),
                    (width or 0),
                    (height or 0))
        return None

    def get_image(self, key):
        key = self.form_key(key)
        if key:
            if key in self.image_objects:
                self.url_cache.touch(key=key)
                return self.image_objects[key]
        return None

    def set_image(self, key, image, owner):
        key = self.form_key(key)
        if key in self.image_objects:
            if owner not in self.current_owners[key] \
               or len(self.current_owners[key]) > 1:
                for other_owner in self.current_owners[key]:
                    if other_owner != owner:
                        self.keep_old_copy(other_owner, image, key)
            if owner in self.old_objects:
                for pair in self.old_objects[owner]:
                    if pair[0] == key:
                        self.old_objects[owner].remove(pair)
        self.image_objects[key] = image
        self.current_owners[key] = [owner]

    def keep_old_copy(self, owner, image, key):
        key = self.form_key(key)
        self.old_objects.setdefault(owner, []).append((key,image))

    def owner_exiting(self, owner):
        del self.old_objects[owner]
