'''Errores personalizados del proyecto'''

class LoadConfigError(Exception):
    pass

class EmptyConfigError(Exception):
    pass

class MissingEnvVarError(Exception):
    pass

class ExtractError(Exception):
    pass

class PersistFileError(Exception):
    pass