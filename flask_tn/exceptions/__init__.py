
class InvalidFileException(Exception):
    """Exception raised for input file errors

    Attributes:
        file -- file path
        message -- explanation of the error
    """

    def __init__(self, file_path, message="The provided file is invalid."):
        self.file_path = file_path
        self.message = message
        super().__init__(self.message)