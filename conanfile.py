import os

from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration

class LibkmlConan(ConanFile):
    name = "libkml"
    description = "Reference implementation of OGC KML 2.2"
    license = "BSD-3-Clause"
    topics = ("conan", "libkml", "kml", "ogc", "geospatial")
    homepage = "https://github.com/libkml/libkml"
    url = "https://github.com/conan-io/conan-center-index"
    exports_sources = ["CMakeLists.txt", "patches/**"]
    generators = "cmake", "cmake_find_package"
    settings = "os", "arch", "compiler", "build_type"
    requires = ["boost/1.72.0", "expat/2.2.9", "minizip/1.2.11", "uriparser/0.9.3", "zlib/1.2.11"]
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    @property
    def _build_subfolder(self):
        return "build_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        os.rename(self.name + "-" + self.version, self._source_subfolder)
        for patch in self.conan_data["patches"][self.version]:
            tools.patch(**patch)

        cstring_files = [
            os.path.join(self._source_subfolder, "src", "kml", "base", "file_posix.cc"),
            os.path.join(self._source_subfolder, "src", "kml", "base", "string_util.cc"),
            os.path.join(self._source_subfolder, "src", "kml", "base", "uri_parser.cc"),
        ]
        for cstring_file in cstring_files:
            tools.replace_in_file(cstring_file, "#include <string.h>", "include <cstring>")
            tools.replace_in_file(cstring_file, "strlen", "std::strlen") # file_posix.cc
            tools.replace_in_file(cstring_file, "memcpy", "std::memcpy") # string_util.cc
            tools.replace_in_file(cstring_file, "strchr", "std::strchr") # string_util.cc
            tools.replace_in_file(cstring_file, "memset", "std::memset") # uri_parser.cc
        tools.replace_in_file(self._source_subfolder, "src", "kml", "dom", "kml_handler_ns.cc",
                              "#include <cstring>  // For strchr().",
                              "")

        os.remove(os.path.join(self._source_subfolder, "cmake", "FindMiniZip.cmake"))
        os.remove(os.path.join(self._source_subfolder, "cmake", "FindUriParser.cmake"))

    def build(self):
        cmake = self._configure_cmake()
        cmake.build()

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.configure(build_folder=self._build_subfolder, source_folder=self._source_subfolder)
        return cmake

    def package(self):
        self.copy("COPYING", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
        tools.rmdir(os.path.join(self.package_folder, "cmake"))

    def package_info(self):
        gen_libs = tools.collect_libs(self)

        # Libs ordered following linkage order:
        # - kmlconvenience is a dependency of kmlregionator
        # - kmlengine is a dependency of kmlregionator and kmlconvenience
        # - kmldom is a dependency of kmlregionator, kmlconvenience and kmlengine
        # - kmlbase is a dependency of kmlregionator, kmlconvenience, kmlengine, kmldom and kmlxsd
        lib_list = ["kmlregionator", "kmlconvenience", "kmlengine", "kmldom", "kmlxsd", "kmlbase"]

        # List of lists, so if more than one matches the lib both will be added to the list
        ordered_libs = [[] for _ in range(len(lib_list))]

        # The order is important, reorder following the lib_list order
        missing_order_info = []
        for real_lib_name in gen_libs:
            for pos, alib in enumerate(lib_list):
                if os.path.splitext(real_lib_name)[0].split("-")[0].endswith(alib):
                    ordered_libs[pos].append(real_lib_name)
                    break
            else:
                missing_order_info.append(real_lib_name)

        # Flat the list
        self.cpp_info.libs = [item for sublist in ordered_libs
                                      for item in sublist if sublist] + missing_order_info

        self.output.info("LIBRARIES: %s" % self.cpp_info.libs)
