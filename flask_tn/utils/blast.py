from typing import List

class AlignmentPart:
    def __init__(self):
        self.start = 0
        self.end = 0
        self.strand = "+"
        self.sequence = ""

    @property
    def start(self) -> int:
        # Getter method for the attribute 'start'.
        return self.__start

    @start.setter
    def start(self, value):
        # Setter method for the attribute 'start'.
        self.__start = value

    @property
    def end(self) -> int:
        return self.__end

    @end.setter
    def end(self, value):
        self.__end = value

    @property
    def strand(self) -> str:
        return self.__strand

    @strand.setter
    def strand(self, value):
        self.__strand = value

    @property
    def sequence(self) -> str:
        return self.__sequence

    @sequence.setter
    def sequence(self, value):
        self.__sequence = value

    def as_dict(self):
        return {
            "start": self.start,
            "end": self.end,
            "strand": self.strand,
            "sequence": self.sequence,
        }

class HighScoringPair:
    # query cover (query length divided by identity)
    def __init__(self):
        self.score = 0
        self.expect = 0
        self.gaps = 0
        self.identity = 0
        self.queryAlignment = AlignmentPart()  # AlignmentPart
        self.subjectAlignment = AlignmentPart()  # AlignmentPart

    @property
    def score(self) -> int:
        return self.__score

    @score.setter
    def score(self, value):
        self.__score = value
    
    @property
    def expect(self) -> int:
        return self.__expect

    @expect.setter
    def expect(self, value):
        self.__expect = value
    
    @property
    def gaps(self) -> int:
        return self.__gaps

    @gaps.setter
    def gaps(self, value):
        self.__gaps = value
    
    @property
    def identity(self) -> int:
        return self.__identity

    @identity.setter
    def identity(self, value):
        self.__identity = value
    
    @property
    def queryAlignment(self) -> AlignmentPart:
        return self.__queryAlignment

    @queryAlignment.setter
    def queryAlignment(self, value):
        self.__queryAlignment = value
    
    @property
    def subjectAlignment(self) -> AlignmentPart:
        return self.__subjectAlignment

    @subjectAlignment.setter
    def subjectAlignment(self, value):
        self.__subjectAlignment = value
    
    def as_dict(self):
        return {
            "score": self.score,
            "expect": self.end,
            "gaps": self.gaps,
            "identity": self.identity,
            "query_alignment": self.queryAlignment.as_dict(),
            "subject_alignment": self.subjectAlignment.as_dict(),
        }

class SubjectAlignments:
    # subject: Tn6246-KP834591.1
    # subject total length: Length=5148
    # length: Length=5148
    def __init__(self):
        self.subjectName: str = ""
        self.subjectSequence: str = ""
        self.__hsps: HighScoringPair = []
    
    @property
    def subjectName(self) -> str:
        return self.__subjectName

    @subjectName.setter
    def subjectName(self, value):
        self.__subjectName = value
    
    @property
    def subjectSequence(self) -> str:
        return self.__subjectSequence

    @subjectSequence.setter
    def subjectSequence(self, value):
        self.__subjectSequence = value
    
    @property
    def hsps(self) -> List[HighScoringPair]:
        return self.__hsps

    def max_score(self) -> int:
        if len(self.hsps) == 0:
            return -1
        
        i = len(self.hsps)-1
        max_score = -1
        while i >= 0:
            if self.hsps[i].score > max_score:
                max_score = self.hsps[i].score
            i = i - 1

        return max_score
    
    def total_score(self) -> int:
        if len(self.hsps) == 0:
            return -1
        
        total_score = -1
        i = len(self.hsps)-1
        while i >= 0:
            total_score += self.hsps[i].score
            i = i - 1

        return total_score

    def as_dict(self):
        return {
            "subject_name": self.subjectName,
            "subject_sequence": self.subjectSequence,
            "hsps": [x.to_dict() for x in self.hsps]
        }

class BlastResult:
    def __init__(self):
        self.queryLength: int = 0
        self.blastVersion: str = ""
        self.__subjectAlignments: SubjectAlignments = []

    @property
    def queryLength(self) -> int:
        return self.__queryLength

    @queryLength.setter
    def queryLength(self, value):
        self.__queryLength = value
    
    @property
    def blastVersion(self) -> str:
        return self.__blastVersion

    @blastVersion.setter
    def blastVersion(self, value):
        self.__blastVersion = value

    @property
    def subjectAlignments(self) -> List[SubjectAlignments]:
        return self.__subjectAlignments

    def as_dict(self):
        return {
            "query_length": self.queryLength,
            "blast_version": self.blastVersion,
            "alignments": [x.to_dict() for x in self.subjectAlignments]
        }
    
def get_blast_obj(filepath):
    blastResult = BlastResult()
    with open(filepath, "r", encoding="latin1") as reader:
        line = reader.readline().strip("\n")        
        blastResult.blastVersion=line
        while not line.startswith("Length="):
            line = reader.readline()
        line = line.strip("\n")
        cols = line.split("=")
        blastResult.queryLength = int(cols[1])
        # read until the alignments
        while not line.startswith(">"):
            line = reader.readline()