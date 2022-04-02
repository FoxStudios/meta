import datetime
import json
import os

import iso8601
from .jsonobject import *
from .common import polymc_path

PMC_DIR = polymc_path()


class ISOTimestampProperty(AbstractDateProperty):
    _type = datetime.datetime

    def _wrap(self, value):
        try:
            return iso8601.parse_date(value)
        except ValueError as e:
            raise ValueError(
                'Invalid ISO date/time {0!r} [{1}]'.format(value, e))

    def _unwrap(self, value):
        return value, value.isoformat()


class GradleSpecifier:
    '''
        A gradle specifier - a maven coordinate. Like one of these:
        "org.lwjgl.lwjgl:lwjgl:2.9.0"
        "net.java.jinput:jinput:2.0.5"
        "net.minecraft:launchwrapper:1.5"
    '''

    def __init__(self, name):
        atSplit = name.split('@')

        components = atSplit[0].split(':')
        self.group = components[0]
        self.artifact = components[1]
        self.version = components[2]

        self.extension = 'jar'
        if len(atSplit) == 2:
            self.extension = atSplit[1]

        if len(components) == 4:
            self.classifier = components[3]
        else:
            self.classifier = None

    def toString(self):
        extensionStr = ''
        if self.extension != 'jar':
            extensionStr = "@%s" % self.extension
        if self.classifier:
            return "%s:%s:%s:%s%s" % (self.group, self.artifact, self.version, self.classifier, extensionStr)
        else:
            return "%s:%s:%s%s" % (self.group, self.artifact, self.version, extensionStr)

    def getFilename(self):
        if self.classifier:
            return "%s-%s-%s.%s" % (self.artifact, self.version, self.classifier, self.extension)
        else:
            return "%s-%s.%s" % (self.artifact, self.version, self.extension)

    def getBase(self):
        return "%s/%s/%s/" % (self.group.replace('.', '/'), self.artifact, self.version)

    def getPath(self):
        return self.getBase() + self.getFilename()

    def __repr__(self):
        return "GradleSpecifier('" + self.toString() + "')"

    def isLwjgl(self):
        return self.group in ("org.lwjgl", "org.lwjgl.lwjgl", "net.java.jinput", "net.java.jutils")

    def isLog4j(self):
        return self.group == "org.apache.logging.log4j"

    def __lt__(self, other):
        return self.toString() < other.toString()

    def __eq__(self, other):
        return self.group == other.group and self.artifact == other.artifact and self.version == other.version and self.classifier == other.classifier

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.toString().__hash__()


class GradleSpecifierProperty(JsonProperty):
    def wrap(self, value):
        return GradleSpecifier(value)

    def unwrap(self, value):
        return value, value.toString()


class MojangArtifactBase(JsonObject):
    sha1 = StringProperty(exclude_if_none=True, default=None)
    size = IntegerProperty(exclude_if_none=True, default=None)
    url = StringProperty()


class MojangArtifact(MojangArtifactBase):
    path = StringProperty(exclude_if_none=True, default=None)


class MojangAssets(MojangArtifactBase):
    id = StringProperty()
    totalSize = IntegerProperty()


class MojangLibraryDownloads(JsonObject):
    artifact = ObjectProperty(MojangArtifact, exclude_if_none=True, default=None)
    classifiers = DictProperty(MojangArtifact, exclude_if_none=True, default=None)


class MojangLibraryExtractRules(JsonObject):
    exclude = ListProperty(StringProperty)


'''
            "rules": [
                {
                    "action": "allow"
                },
                {
                    "action": "disallow",
                    "os": {
                        "name": "osx"
                    }
                }
            ]
'''


class OSRule(JsonObject):
    name = StringProperty(choices=["osx", "linux", "windows"], required=True)
    version = StringProperty(exclude_if_none=True, default=None)


class MojangRule(JsonObject):
    action = StringProperty(choices=["allow", "disallow"], required=True)
    os = ObjectProperty(OSRule, exclude_if_none=True, default=None)


class MojangLibrary(JsonObject):
    extract = ObjectProperty(MojangLibraryExtractRules, exclude_if_none=True, default=None)
    name = GradleSpecifierProperty(required=True)
    downloads = ObjectProperty(MojangLibraryDownloads, exclude_if_none=True, default=None)
    natives = DictProperty(StringProperty, exclude_if_none=True, default=None)
    rules = ListProperty(MojangRule, exclude_if_none=True, default=None)


class MojangLoggingArtifact(MojangArtifactBase):
    id = StringProperty()


class MojangLogging(JsonObject):
    file = ObjectProperty(MojangLoggingArtifact, required=True)
    argument = StringProperty(required=True)
    type = StringProperty(required=True, choices=["log4j2-xml"])


class MojangArguments(JsonObject):
    game = ListProperty(exclude_if_none=True, default=None)
    jvm = ListProperty(exclude_if_none=True, default=None)


class JavaVersion(JsonObject):
    component = StringProperty(default="jre-legacy")
    majorVersion = IntegerProperty(default=8)


class UnknownVersionException(Exception):
    """Exception raised for unknown Mojang version file format versions.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


def validateSupportedMojangVersion(version):
    supportedVersion = 21
    if version > supportedVersion:
        raise UnknownVersionException(
            "Unsupported Mojang format version: %d. Max supported is: %d" % (version, supportedVersion))


class MojangVersionFile(JsonObject):
    arguments = ObjectProperty(MojangArguments, exclude_if_none=True, default=None)
    assetIndex = ObjectProperty(MojangAssets, exclude_if_none=True, default=None)
    assets = StringProperty(exclude_if_none=True, default=None)
    downloads = DictProperty(MojangArtifactBase, exclude_if_none=True, default=None)
    id = StringProperty(exclude_if_none=True, default=None)
    libraries = ListProperty(MojangLibrary, exclude_if_none=True, default=None)
    mainClass = StringProperty(exclude_if_none=True, default=None)
    processArguments = StringProperty(exclude_if_none=True, default=None)
    minecraftArguments = StringProperty(exclude_if_none=True, default=None)
    minimumLauncherVersion = IntegerProperty(exclude_if_none=True, default=None,
                                             validators=validateSupportedMojangVersion)
    releaseTime = ISOTimestampProperty(exclude_if_none=True, default=None)
    time = ISOTimestampProperty(exclude_if_none=True, default=None)
    type = StringProperty(exclude_if_none=True, default=None)
    inheritsFrom = StringProperty(exclude_if_none=True, default=None)
    logging = DictProperty(MojangLogging, exclude_if_none=True, default=None)
    complianceLevel = IntegerProperty(exclude_if_none=True, default=None)
    javaVersion = ObjectProperty(JavaVersion, exclude_if_none=True, default=None)


CurrentPolyMCFormatVersion = 1


def validateSupportedPolyMCVersion(version):
    if version > CurrentPolyMCFormatVersion:
        raise UnknownVersionException(
            "Unsupported PolyMC format version: %d. Max supported is: %d" % (version, CurrentPolyMCFormatVersion))


class PolyMCLibrary(MojangLibrary):
    url = StringProperty(exclude_if_none=True, default=None)
    mmcHint = StringProperty(name="MMC-hint", exclude_if_none=True, default=None)  # this is supposed to be MMC-hint!


class VersionedJsonObject(JsonObject):
    formatVersion = IntegerProperty(default=CurrentPolyMCFormatVersion, validators=validateSupportedPolyMCVersion)


class DependencyEntry(JsonObject):
    uid = StringProperty(required=True)
    equals = StringProperty(exclude_if_none=True, default=None)
    suggests = StringProperty(exclude_if_none=True, default=None)


class PolyMCVersionFile(VersionedJsonObject):
    name = StringProperty(required=True)
    version = StringProperty(required=True)
    uid = StringProperty(required=True)
    requires = ListProperty(DependencyEntry, exclude_if_none=True, default=None)
    conflicts = ListProperty(DependencyEntry, exclude_if_none=True, default=None)
    volatile = BooleanProperty(exclude_if_none=True, default=None)
    assetIndex = ObjectProperty(MojangAssets, exclude_if_none=True, default=None)
    libraries = ListProperty(PolyMCLibrary, exclude_if_none=True, default=None)
    mavenFiles = ListProperty(PolyMCLibrary, exclude_if_none=True, default=None)
    mainJar = ObjectProperty(PolyMCLibrary, exclude_if_none=True, default=None)
    jarMods = ListProperty(PolyMCLibrary, exclude_if_none=True, default=None)
    mainClass = StringProperty(exclude_if_none=True, default=None)
    appletClass = StringProperty(exclude_if_none=True, default=None)
    minecraftArguments = StringProperty(exclude_if_none=True, default=None)
    releaseTime = ISOTimestampProperty(exclude_if_none=True, default=None)
    type = StringProperty(exclude_if_none=True, default=None)
    addTraits = ListProperty(StringProperty, name="+traits", exclude_if_none=True, default=None)
    addTweakers = ListProperty(StringProperty, name="+tweakers", exclude_if_none=True, default=None)
    order = IntegerProperty(exclude_if_none=True, default=None)


class PolyMCSharedPackageData(VersionedJsonObject):
    name = StringProperty(required=True)
    uid = StringProperty(required=True)
    recommended = ListProperty(StringProperty, exclude_if_none=True, default=None)
    authors = ListProperty(StringProperty, exclude_if_none=True, default=None)
    description = StringProperty(exclude_if_none=True, default=None)
    projectUrl = StringProperty(exclude_if_none=True, default=None)

    def write(self):
        try:
            with open(PMC_DIR + "/%s/package.json" % self.uid, 'w') as file:
                json.dump(self.to_json(), file, sort_keys=True, indent=4)
        except EnvironmentError as e:
            print("Error while trying to save shared packaged data for %s:" % self.uid, e)


def readSharedPackageData(uid):
    with open(PMC_DIR + "/%s/package.json" % uid, 'r') as file:
        return PolyMCSharedPackageData(json.load(file))


class PolyMCVersionIndexEntry(JsonObject):
    version = StringProperty()
    type = StringProperty(exclude_if_none=True, default=None)
    releaseTime = ISOTimestampProperty()
    requires = ListProperty(DependencyEntry, exclude_if_none=True, default=None)
    conflicts = ListProperty(DependencyEntry, exclude_if_none=True, default=None)
    recommended = BooleanProperty(exclude_if_none=True, default=None)
    volatile = BooleanProperty(exclude_if_none=True, default=None)
    sha256 = StringProperty()


class PolyMCVersionIndex(VersionedJsonObject):
    name = StringProperty()
    uid = StringProperty()
    versions = ListProperty(PolyMCVersionIndexEntry)


class PolyMCPackageIndexEntry(JsonObject):
    name = StringProperty()
    uid = StringProperty()
    sha256 = StringProperty()


class PolyMCPackageIndex(VersionedJsonObject):
    packages = ListProperty(PolyMCPackageIndexEntry)
