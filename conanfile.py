from conan import ConanFile, conan_version
from conan.tools.cmake import CMakeDeps, CMakeToolchain, CMake, cmake_layout
from conan.errors import ConanInvalidConfiguration, ConanException
from conan import tools
import os
import yaml


class NcbiCxxToolkit(ConanFile):
    name = "ncbi-cxx-toolkit-public"
    license = "CC0-1.0"
    homepage = "https://ncbi.github.io/cxx-toolkit"
    url = "https://github.com/ncbi/ncbi-cxx-toolkit-conan.git"
    description = "NCBI C++ Toolkit -- a cross-platform application framework and a collection of libraries for working with biological data."
    topics = ("ncbi", "biotechnology", "bioinformatics", "genbank", "gene",
              "genome", "genetic", "sequence", "alignment", "blast",
              "biological", "toolkit", "c++")
    settings = "os", "compiler", "build_type", "arch"
    short_paths = False
    tk_dependencies = None
    tk_requirements = None
    tk_componenttargets = set()

    options = {
        "shared":     [True, False],
        "fPIC":       [True, False],
        "with_projects": ["ANY"],
        "with_targets":  ["ANY"],
        "with_tags":     ["ANY"],
        "with_components": ["ANY"],
        "with_local": [True, False],
        "with_internal": [True, False]
    }
    default_options = {
        "shared":     False,
        "fPIC":       True,
        "with_projects":  "",
        "with_targets":   "",
        "with_tags":      "",
        "with_components": "",
        "with_local": False,
        "with_internal": False
    }

#----------------------------------------------------------------------------
#    def set_version(self):
#        if self.version == None:
#            self.version = "0.0.0"

    def export(self):
        tools.files.copy(self, self._dependencies_filename,
            os.path.join(self.recipe_folder, self._dependencies_folder),
            os.path.join(self.export_folder, self._dependencies_folder))
        tools.files.copy(self, self._requirements_filename,
            os.path.join(self.recipe_folder, self._dependencies_folder),
            os.path.join(self.export_folder, self._dependencies_folder))

#----------------------------------------------------------------------------
    @property
    def _source_subfolder(self):
        return "src"

    @property
    def _dependencies_folder(self):
        return "dependencies"

    @property
    def _dependencies_filename(self):
        return "dependencies-{}.{}.yml".format(tools.scm.Version(self.version).major, tools.scm.Version(self.version).minor)

    @property
    def _requirements_filename(self):
        return "requirements-{}.{}.yml".format(tools.scm.Version(self.version).major, tools.scm.Version(self.version).minor)

    @property
    def _tk_dependencies(self):
        if self.tk_dependencies is None:
            dependencies_filepath = os.path.join(self.recipe_folder, self._dependencies_folder, self._dependencies_filename)
            if not os.path.isfile(dependencies_filepath):
                raise ConanException("Cannot find {}".format(dependencies_filepath))
            self.tk_dependencies = yaml.safe_load(open(dependencies_filepath))
        return self.tk_dependencies

    @property
    def _tk_requirements(self):
        if self.tk_requirements is None:
            requirements_filepath = os.path.join(self.recipe_folder, self._dependencies_folder, self._requirements_filename)
            if not os.path.isfile(requirements_filepath):
                raise ConanException("Cannot find {}".format(requirements_filepath))
            self.tk_requirements = yaml.safe_load(open(requirements_filepath))
        return self.tk_requirements

#----------------------------------------------------------------------------
    def _translate_req(self, key):
        if "Boost" in key:
            key = "Boost"
        if key in self._tk_requirements["disabled"].keys():
            if self.settings.os in self._tk_requirements["disabled"][key]:
                return None
        if self.options.with_internal:
            if key in self._tk_requirements["internal-requirements"].keys():
                return self._tk_requirements["internal-requirements"][key]
        if key in self._tk_requirements["requirements"].keys():
            return self._tk_requirements["requirements"][key]
        return None

    def _parse_option(self, data):
        _res = set()
        if data != "":
            _data = str(data)
            _data = _data.replace(",", ";")
            _data = _data.replace(" ", ";")
            _res.update(_data.split(";"))
            if "" in _res:
                _res.remove("")
        return _res

#----------------------------------------------------------------------------
    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            tools.build.check_min_cppstd(self, 17)
        if self.settings.os not in ["Linux", "Macos", "Windows"]:   
            raise ConanInvalidConfiguration("This operating system is not supported")
        if tools.microsoft.is_msvc(self):
            tools.microsoft.check_min_vs(self, "190")
            if self.options.shared and tools.microsoft.is_msvc_static_runtime(self):
                raise ConanInvalidConfiguration("This configuration is not supported")
        if self.settings.compiler == "gcc" and tools.scm.Version(self.settings.compiler.version) < "7":
            raise ConanInvalidConfiguration("This version of GCC is not supported")
        if tools.build.cross_building(self):
            raise ConanInvalidConfiguration("Cross compilation is not supported")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if "options" in self._tk_requirements.keys():
            for pkg in self._tk_requirements["options"]:
                dest = vars(self.options[pkg + "*"])["_dict" if conan_version.major == "1" else "_data"]
                options = self._tk_requirements["options"][pkg]
                for opt in options.keys():
                    dest[opt] = options[opt]

    def layout(self):
       cmake_layout(self)
       self.folders.source = self._source_subfolder

#----------------------------------------------------------------------------
#    def build_requirements(self):
#        if cross_building(self):
#            self.tool_requires("{}/{}".format(self.name, self.version))

    def requirements(self):
        _alltargets = self._parse_option(self.options.with_targets)
        _required_components = set()
        for _t in _alltargets:
            for _component in self._tk_dependencies["components"]:
                _libraries = self._tk_dependencies["libraries"][_component]
                if _t in _libraries:
                    _required_components.add(_component)
                    break

        _allcomponents = self._parse_option(self.options.with_components)
        _required_components.update(_allcomponents)

        if len(_required_components) > 0:
            _todo = _required_components.copy()
            _required_components.clear()
            _next = set()
            while len(_todo) > 0:
                for _component in _todo:
                    if not _component in _required_components:
                        _required_components.add(_component)
                        if _component in self._tk_dependencies["dependencies"].keys():
                            for _n in self._tk_dependencies["dependencies"][_component]:
                                if not _n in _required_components:
                                    _next.add(_n)
                _todo = _next.copy()
                _next.clear()

        if len(_required_components) == 0:
            _required_components.update( self._tk_dependencies["components"])
        else:
            for component in _required_components:
                self.tk_componenttargets.update(self._tk_dependencies["libraries"][component])

        requirements = set()
        for component in _required_components:
            libraries = self._tk_dependencies["libraries"][component]
            for lib in libraries:
                if lib in self._tk_dependencies["requirements"].keys():
                    requirements.update(self._tk_dependencies["requirements"][lib])

        for req in requirements:
            pkgs = self._translate_req(req)
            if pkgs is not None:
                for pkg in pkgs:
                    print("Package requires ", pkg)
                    self.requires(pkg)

#----------------------------------------------------------------------------
    def source(self):
        src_found = False;
        print("getting Toolkit sources...")
        tk_url = self.conan_data["sources"][self.version]["url"] if "url" in self.conan_data["sources"][self.version].keys() else ""
        tk_git = self.conan_data["sources"][self.version]["git"] if "git" in self.conan_data["sources"][self.version].keys() else ""
        tk_branch = self.conan_data["sources"][self.version]["branch"] if "branch" in self.conan_data["sources"][self.version].keys() else "main"

        if tk_url != "":
            print("from url: " + tk_url)
            tools.files.get(self, tk_url, strip_root = True)
            src_found = True;

        if not src_found and tk_git != "":
            print("from git: " + tk_git + "/" + tk_branch)
            try:
                git = tools.scm.Git(self)
                git.clone(tk_git, target = ".", args = ["--single-branch", "--branch", tk_branch, "--depth", "1"])
                src_found = True;
            except Exception:
                print("git failed")

        if not src_found:
            raise ConanException("Failed to find the Toolkit sources")
        root = os.path.join(os.getcwd(), "CMakeLists.txt")
        with open(root, "w") as f:
            f.write("cmake_minimum_required(VERSION 3.15)\n")
            f.write("project(ncbi-cpp)\n")
            f.write("include(src/build-system/cmake/CMake.NCBItoolkit.cmake)\n")
            f.write("add_subdirectory(src)\n")

#----------------------------------------------------------------------------
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["NCBI_PTBCFG_PACKAGING"] = True
        if self.options.shared:
            tc.variables["NCBI_PTBCFG_ALLOW_COMPOSITE"] = True
        tc.variables["NCBI_PTBCFG_PROJECT_LIST"] = str(self.options.with_projects) + ";-app/netcache"
        if self.options.with_targets != "":
            tc.variables["NCBI_PTBCFG_PROJECT_TARGETS"] = self.options.with_targets
        if len(self.tk_componenttargets) != 0:
            tc.variables["NCBI_PTBCFG_PROJECT_COMPONENTTARGETS"] = ";".join(self.tk_componenttargets)
        tc.variables["NCBI_PTBCFG_PROJECT_TAGS"] = str(self.options.with_tags) + ";-test;-demo;-sample"
        if self.options.with_local:
            tc.variables["NCBI_PTBCFG_USELOCAL"] = True
        if tools.microsoft.is_msvc(self):
            tc.variables["NCBI_PTBCFG_CONFIGURATION_TYPES"] = self.settings.build_type
        tc.generate()
        cmdep = CMakeDeps(self)
        cmdep.generate()

#----------------------------------------------------------------------------
    def build(self):
        cmake = CMake(self)
        cmake.configure()
# Visual Studio sometimes runs "out of heap space"
        if tools.microsoft.is_msvc(self):
            cmake.parallel = False
        cmake.build()

#----------------------------------------------------------------------------
    def package(self):
        cmake = CMake(self)
        cmake.install()

#----------------------------------------------------------------------------
    def package_info(self):
        impfile = os.path.join(self.package_folder, "res", "ncbi-cpp-toolkit.imports")
        allexports = set(open(impfile).read().split())
        absent = []
        for component in self._tk_dependencies["components"]:
            c_libs = []
            libraries = self._tk_dependencies["libraries"][component]
            for lib in libraries:
                if lib in allexports:
                    c_libs.append(lib)
            if len(c_libs) == 0 and not len(libraries) == 0:
                absent.append(component)
        for component in self._tk_dependencies["components"]:
            c_libs = []
            c_reqs = []
            n_reqs = set()
            c_deps = self._tk_dependencies["dependencies"][component]
            for c in c_deps:
                if c in absent:
                    c_deps.remove(c)
            c_reqs.extend(c_deps)
            libraries = self._tk_dependencies["libraries"][component]
            for lib in libraries:
                if lib in allexports:
                    c_libs.append(lib)
                if lib in self._tk_dependencies["requirements"].keys():
                    n_reqs.update(self._tk_dependencies["requirements"][lib])
            for req in n_reqs:
                pkgs = self._translate_req(req)
                if pkgs is not None:
                    for pkg in pkgs:
                        pkg = pkg[:pkg.find("/")]
                        ref = pkg + "::" + pkg
                        c_reqs.append(ref)
            if not len(c_libs) == 0 or (len(libraries) == 0 and not len(c_reqs) == 0):
                self.cpp_info.components[component].libs = c_libs
                self.cpp_info.components[component].requires = c_reqs

        if self.settings.os == "Windows":
            self.cpp_info.components["core"].defines.append("_UNICODE")
            self.cpp_info.components["core"].defines.append("_CRT_SECURE_NO_WARNINGS=1")
        else:
            self.cpp_info.components["core"].defines.append("_MT")
            self.cpp_info.components["core"].defines.append("_REENTRANT")
            self.cpp_info.components["core"].defines.append("_THREAD_SAFE")
            self.cpp_info.components["core"].defines.append("_FILE_OFFSET_BITS=64")
        if self.options.shared:
            self.cpp_info.components["core"].defines.append("NCBI_DLL_BUILD")
        if self.settings.build_type == "Debug":
            self.cpp_info.components["core"].defines.append("_DEBUG")
        else:
            self.cpp_info.components["core"].defines.append("NDEBUG")
        if self.settings.os == "Windows":
            self.cpp_info.components["core"].system_libs = ["ws2_32", "dbghelp"]
        elif self.settings.os == "Linux":
            self.cpp_info.components["core"].system_libs = ["dl", "rt", "m", "pthread", "resolv"]
        elif self.settings.os == "Macos":
            self.cpp_info.components["core"].system_libs = ["dl", "c", "m", "pthread", "resolv"]
        self.cpp_info.components["core"].builddirs.append("res")
        self.cpp_info.components["core"].build_modules = ["res/build-system/cmake/CMake.NCBIpkg.conan.cmake"]
