from flask_tn.ext.database import db
from sqlalchemy.sql.functions import now
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash

from sqlalchemy import inspect


def drop_all(keep_pubmed: bool = False, keep_user: bool = False) -> None:
    # User.__table__.drop(db.engine)
    array_remove = [
        Te_Entry,
        Te_Fragment,
        Te_Repeat,
        Te_Repeat_Fragment,
        Te_Orf,
        Te_Orf_Fragment,
        Te_RecombSite,
        Te_Recomb_Fragment,
        Orf_Summary,
        Entry_Orf_Summary,
    ]
    if keep_pubmed or keep_user:
        if keep_pubmed and not keep_user:
            array_remove.append(User)
            array_remove.append(UserGenbank)
            array_remove.append(UploadCategory)
            array_remove.append(ChangeLog)
        elif keep_user and not keep_pubmed:
            array_remove.append(Te_Pubmed)
        # tables to delete: Te_Entry
        for to_remove in array_remove:
            if inspect(db.engine).has_table(to_remove.__tablename__):
                to_remove.__table__.drop(db.engine)
        if inspect(db.engine).has_table(Entry_Pubmed.name):
            Entry_Pubmed.drop(db.engine)
    else:
        db.drop_all()


def delete_all(keep_user=False):
    entries = Te_Entry.query.filter_by(in_production=1)
    db.session.delete(entries)
    db.session.commit()
    if not keep_user:
        entries = Te_Entry.query.filter_by(in_production=0)
        db.session.delete(entries)


class Te_Base(object):
    def get_value(self, variable):
        return self.__getattribute__(variable)

    def has_attribute(self, variable):
        return hasattr(self, variable)

    def set_value(self, variable, value):
        self.__setattr__(variable, value)

    def get_direction(self):
        direction = "+"
        if self.start > self.end:
            direction = "-"
        return direction

    def format_sequence(self, chunk_size):
        col_len = chunk_size
        my_list = [
            self.sequence[i : i + col_len]
            for i in range(0, len(self.sequence), col_len)
        ]
        new_sequence = " ".join(my_list)
        return new_sequence


class Te_Base_Fragment(object):
    start = db.Column(db.Integer, nullable=True)
    end = db.Column(db.Integer, nullable=True)
    strand = db.Column(db.String, nullable=True)


Entry_Pubmed = db.Table(
    "entry_pubmed",
    db.Column(
        "pubmed_id",
        db.Integer,
        db.ForeignKey("te_pubmed.pubmed_id"),
        primary_key=True,
    ),
    db.Column(
        "entry_id", db.Integer, db.ForeignKey("te_entry.entry_id"), primary_key=True
    ),
)


class Te_Entry(db.Model, Te_Base):
    __tablename__ = "te_entry"
    entry_id = db.Column(db.Integer, nullable=False, primary_key=True)
    entry_id_parent = db.Column(
        db.Integer, db.ForeignKey("te_entry.entry_id"), nullable=True
    )
    in_production = db.Column(
        db.Integer, nullable=True, default=1
    )  # boolean | 0 or 1 | First Isolate?

    start = db.Column(db.Integer, nullable=True)
    end = db.Column(db.Integer, nullable=True)

    # label = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)

    # te_first = db.Column(db.Integer, nullable=True) # boolean | 0 or 1 | First Isolate?
    first_isolate = db.Column(
        db.Integer, nullable=True
    )  # boolean | 0 or 1 | First Isolate?
    capture = db.Column(db.Integer, nullable=True)  # boolean | 0 or 1
    partial = db.Column(db.Integer, nullable=True)  # boolean | 0 or 1
    transposition = db.Column(db.Integer, nullable=True)  # boolean | 0 or 1
    accession = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    display_name = db.Column(db.String(50), nullable=True)
    family = db.Column(db.String(50), nullable=True)
    group = db.Column(db.String(50), nullable=True)
    synonyms = db.Column(
        db.String(50), nullable=True
    )  # multiple, it can be foreign key
    organism = db.Column(db.String(250), nullable=True)  # it can be a foreign key
    taxonomy = db.Column(db.String(50), nullable=True)  # it can be a foreign key
    comment = db.Column(db.String(250), nullable=True)
    bacteria_group = db.Column(db.String(50), nullable=True)
    molecular_source = db.Column(db.String(50), nullable=True)
    region = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    other_loc = db.Column(db.String, nullable=True)
    date = db.Column(db.String(250), nullable=True)

    parents = db.relationship("Te_Entry", remote_side=[entry_id])

    repeats = db.relationship(
        "Te_Repeat", backref="te_entry", lazy="dynamic", cascade="all, delete-orphan"
    )

    fragments = db.relationship(
        "Te_Fragment", backref="te_entry", lazy="dynamic", cascade="all, delete-orphan"
    )

    orfs = db.relationship(
        "Te_Orf", backref="te_entry", lazy="dynamic", cascade="all, delete-orphan"
    )

    recombs = db.relationship(
        "Te_RecombSite",
        backref="te_entry",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    user_gb = db.relationship(
        "UserGenbank", backref="te_entry", lazy="dynamic", cascade="all, delete-orphan"
    )

    pubmeds = db.relationship(
        "Te_Pubmed",
        secondary=Entry_Pubmed,
        # lazy="subquery",
        # backref=db.backref("te_entry", lazy=True)
        lazy="dynamic",
        backref=db.backref("te_entry"),
    )

    def copy(self):
        new_obj = Te_Entry()

        new_obj.type = self.type
        new_obj.first_isolate = self.first_isolate
        new_obj.capture = self.capture
        new_obj.partial = self.partial
        new_obj.transposition = self.transposition
        new_obj.accession = self.accession
        new_obj.name = self.name
        new_obj.display_name = self.display_name
        new_obj.family = self.family
        new_obj.group = self.group
        new_obj.synonyms = self.synonyms
        new_obj.organism = self.organism
        new_obj.taxonomy = self.taxonomy
        new_obj.comment = self.comment
        new_obj.bacteria_group = self.bacteria_group
        new_obj.molecular_source = self.molecular_source
        new_obj.region = self.region
        new_obj.country = self.country
        new_obj.other_loc = self.other_loc
        new_obj.date = self.date

        for fragment in self.fragments:
            new_fragment = fragment.copy()
            new_obj.fragments.add(new_fragment)

        for repeat in self.repeats:
            new_repeat = repeat.copy()
            new_obj.repeats.add(new_repeat)

        for orf in self.orfs:
            new_orf = orf.copy()
            new_obj.orfs.add(new_orf)

        for recomb in self.recombs:
            new_repeat = recomb.copy()
            new_obj.recombs.add(new_repeat)

        for pubmed in self.pubmeds.all():
            # pub_obj = Te_Pubmed()
            # pub_obj.pubmed_id = int(pubmed.pubmed_id)
            new_obj.pubmeds.add(pubmed)
        return new_obj

    def yes_or_no(self, value):
        retorno = ""
        if value == 1:
            retorno = "Yes"
        elif value == 0:
            retorno = "No"
        else:
            return "ND"
        return retorno

    def as_csv(self):
        string_return = f"{self.accession},{self.name},{self.synonyms}"
        string_return += f",{self.type},{self.family},{self.group}"
        string_return += f",{self.organism},{self.country},{self.date}"
        return string_return

    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            "id": self.entry_id,
            "accession": self.accession,
            "name": self.name,
            "synonyms": self.synonyms,
            "type": self.type,
            "family": self.family,
            "group": self.group,
            "organism": self.organism,
            "country": self.country,
            "date": self.date,
        }

    def datatable(self):
        """Return object data in easily serializable format"""
        return {
            "select": "",
            "accession": self.accession,
            "name": self.name,
            "synonyms": self.synonyms,
            "type": self.type,
            "family": self.family,
            "group": self.group,
            "organism": self.organism,
            "country": self.country,
            "date": self.date,
        }

    def __repr__(self):
        return_str = f"accession {self.accession}\n"
        return_str += f"type {self.type}\n"
        return_str += f"name {self.name}\n"
        return_str += f"family {self.family}\n"
        return return_str


class Te_Fragment(db.Model, Te_Base_Fragment):
    __tablename__ = "te_fragment"
    fragment_id = db.Column(db.Integer, nullable=False, primary_key=True)
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("te_entry.entry_id", ondelete="CASCADE"),
        nullable=False,
    )

    def copy(self):
        new_obj = Te_Fragment()
        new_obj.start = self.start
        new_obj.end = self.end
        new_obj.strand = self.strand
        return new_obj

    def __repr__(self):
        return "Te_Fragment({!r})".format(self.__dict__)


class Te_Repeat_Fragment(db.Model, Te_Base_Fragment):
    __tablename__ = "te_repeat_fragment"
    fragment_id = db.Column(db.Integer, nullable=False, primary_key=True)
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("te_repeat.repeat_id", ondelete="CASCADE"),
        nullable=False,
    )

    def copy(self):
        new_obj = Te_Repeat_Fragment()
        new_obj.start = self.start
        new_obj.end = self.end
        new_obj.strand = self.strand
        return new_obj

    def __repr__(self):
        return "Repeat_Fragment({!r})".format(self.__dict__)


class Te_Recomb_Fragment(db.Model, Te_Base_Fragment):
    __tablename__ = "te_res_fragment"
    fragment_id = db.Column(db.Integer, nullable=False, primary_key=True)
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("te_res.recomb_id", ondelete="CASCADE"),
        nullable=False,
    )

    def copy(self):
        new_obj = Te_Recomb_Fragment()
        new_obj.start = self.start
        new_obj.end = self.end
        new_obj.strand = self.strand
        return new_obj

    def __repr__(self):
        return "Recomb_Fragment({!r})".format(self.__dict__)


class Te_Orf_Fragment(db.Model, Te_Base_Fragment):
    __tablename__ = "te_orf_fragment"
    fragment_id = db.Column(db.Integer, nullable=False, primary_key=True)
    parent_id = db.Column(
        db.Integer, db.ForeignKey("te_orf.orf_id", ondelete="CASCADE"), nullable=False
    )

    def copy(self):
        new_obj = Te_Orf_Fragment()
        new_obj.start = self.start
        new_obj.end = self.end
        new_obj.strand = self.strand
        return new_obj

    def __repr__(self):
        return "Orf_Fragment({!r})".format(self.__dict__)


class Te_Repeat(db.Model, Te_Base):
    __tablename__ = "te_repeat"
    repeat_id = db.Column(db.Integer, nullable=False, primary_key=True)
    entry_id = db.Column(
        db.Integer,
        db.ForeignKey("te_entry.entry_id", ondelete="CASCADE"),
        nullable=False,
    )

    start = db.Column(db.Integer, nullable=True)
    end = db.Column(db.Integer, nullable=True)
    strand = db.Column(db.String, nullable=True)

    associated_te = db.Column(db.String, nullable=True)

    name = db.Column(db.String, nullable=True)
    display_name = db.Column(db.String, nullable=True)
    library_name = db.Column(db.String, nullable=True)
    sequence = db.Column(db.String, nullable=False)
    comment = db.Column(db.String, nullable=True)

    fragments = db.relationship(
        "Te_Repeat_Fragment",
        backref="te_repeat",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def copy(self):
        new_obj = Te_Repeat()
        new_obj.associated_te = self.associated_te
        new_obj.name = self.name
        new_obj.display_name = self.display_name
        new_obj.library_name = self.library_name
        new_obj.sequence = self.sequence
        new_obj.comment = self.comment
        for fragment in self.fragments:
            new_fragment = fragment.copy()
            new_obj.fragments.add(new_fragment)
        return new_obj

    def as_info(self):
        dict_return = {
            "id": self.repeat_id,
            "name": self.name,
            "library_name": self.library_name,
            "sequence": self.sequence,
            "comment": self.comment,
            "fragments": [],
        }
        for fragment in self.fragments.all():
            dict_return["fragments"].append(
                {
                    "start": fragment.start,
                    "end": fragment.end,
                    "strand": fragment.strand,
                }
            )
        return dict_return

    def __repr__(self):
        return "Repeat({!r})".format(self.__dict__)


class Te_Orf(db.Model, Te_Base):
    __tablename__ = "te_orf"
    orf_id = db.Column(db.Integer, nullable=False, primary_key=True)
    entry_id = db.Column(
        db.Integer,
        db.ForeignKey("te_entry.entry_id", ondelete="CASCADE"),
        nullable=False,
    )
    start = db.Column(db.Integer, nullable=True)
    end = db.Column(db.Integer, nullable=True)
    strand = db.Column(db.String, nullable=True)

    associated_te = db.Column(db.String, nullable=True)

    name = db.Column(db.String, nullable=False)  # gene qualifier
    display_name = db.Column(db.String, nullable=True)
    library_name = db.Column(db.String, nullable=True)

    protein_name = db.Column(db.String, nullable=True)  # product qualifier
    genbank_id = db.Column(db.String, nullable=True)

    function = db.Column(db.String, nullable=True)

    orf_class = db.Column(db.String, nullable=True)
    subclass = db.Column(db.String, nullable=True)
    sequence_family = db.Column(db.String, nullable=True)
    target = db.Column(db.String, nullable=True)
    chemistry = db.Column(db.String, nullable=True)

    comment = db.Column(db.String, nullable=True)
    sequence = db.Column(db.String, nullable=True)

    fragments = db.relationship(
        "Te_Orf_Fragment",
        backref="te_orf",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def copy(self):
        new_obj = Te_Orf()
        new_obj.associated_te = self.associated_te
        new_obj.name = self.name
        new_obj.display_name = self.display_name
        new_obj.library_name = self.library_name

        new_obj.protein_name = self.library_name
        new_obj.genbank_id = self.genbank_id

        new_obj.function = self.function

        new_obj.orf_class = self.orf_class
        new_obj.subclass = self.subclass
        new_obj.sequence_family = self.sequence_family
        new_obj.target = self.target
        new_obj.chemistry = self.chemistry

        new_obj.sequence = self.sequence
        new_obj.comment = self.comment
        for fragment in self.fragments:
            new_fragment = fragment.copy()
            new_obj.fragments.add(new_fragment)
        return new_obj

    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            "id": "",
            "name": self.name,
            "class": self.orf_class,
            "function": self.subclass,
            "target": self.target,
            #    'accession': self.tn_src.tn_accession
        }

    def as_info(self):
        dict_return = {
            "id": self.orf_id,
            "name": self.name,
            "class": self.orf_class,
            "subclass": self.subclass,
            "function": self.function,
            "sequence_family": self.sequence_family,
            "target": self.target,
            "chemistry": self.chemistry,
            "library_name": self.library_name,
            "comment": self.comment,
            "sequence": self.sequence,
            "fragments": [],
        }
        for fragment in self.fragments.all():
            dict_return["fragments"].append(
                {
                    "start": fragment.start,
                    "end": fragment.end,
                    "strand": fragment.strand,
                }
            )
        return dict_return

    def __repr__(self):
        return "Orf({!r})".format(self.__dict__)


class Te_RecombSite(db.Model, Te_Base):
    __tablename__ = "te_res"
    recomb_id = db.Column(db.Integer, nullable=False, primary_key=True)
    entry_id = db.Column(
        db.Integer,
        db.ForeignKey("te_entry.entry_id", ondelete="CASCADE"),
        nullable=False,
    )
    start = db.Column(db.Integer, nullable=True)
    end = db.Column(db.Integer, nullable=True)
    strand = db.Column(db.String, nullable=True)

    associated_te = db.Column(db.String, nullable=True)

    name = db.Column(db.String, nullable=True)
    display_name = db.Column(db.String, nullable=True)
    library_name = db.Column(db.String, nullable=True)

    sequence = db.Column(db.String, nullable=False)
    comment = db.Column(db.String, nullable=True)

    fragments = db.relationship(
        "Te_Recomb_Fragment",
        backref="te_res",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def copy(self):
        new_obj = Te_RecombSite()
        new_obj.associated_te = self.associated_te
        new_obj.name = self.name
        new_obj.display_name = self.display_name
        new_obj.library_name = self.library_name
        new_obj.sequence = self.sequence
        new_obj.comment = self.comment

        for fragment in self.fragments:
            new_fragment = fragment.copy()
            new_obj.fragments.add(new_fragment)
        return new_obj

    def __repr__(self):
        return "Te_RecombSite({!r})".format(self.__dict__)

    def as_info(self):
        dict_return = {
            "id": self.recomb_id,
            "name": self.name,
            "library_name": self.library_name,
            "comment": self.comment,
            "sequence": self.sequence,
            "fragments": [],
        }
        for fragment in self.fragments.all():
            dict_return["fragments"].append(
                {
                    "start": fragment.start,
                    "end": fragment.end,
                    "strand": fragment.strand,
                }
            )
        return dict_return


class Te_Pubmed(db.Model):
    __tablename__ = "te_pubmed"
    pubmed_id = db.Column(db.Integer, nullable=False, primary_key=True)
    title = db.Column(db.String, nullable=True)
    abstract = db.Column(db.String, nullable=True)
    authors = db.Column(db.String, nullable=True)
    journal = db.Column(db.String, nullable=True)
    summary = db.Column(db.String, nullable=True)

    def to_reference(self):
        s = f"{self.authors}. {self.title}. {self.summary}."
        return s

    def __repr__(self):
        return "Te_Pubmed({!r})".format(self.__dict__)


# # The following table is an attempt to improve the performance of the
# # gene search table
# class Entry_Orf(db.Model):
#     __tablename__ = "entry_orf"
#     id = db.Column(db.Integer, nullable=False, primary_key=True)
#     accession = db.Column(db.String(100), nullable=False, index=True)
#     name = db.Column(db.String(50), nullable=False)
#     organism = db.Column(db.String(250), nullable=True)
#     country =  db.Column(db.String(50), nullable=True)
#     orf_name = db.Column(db.String, nullable=False, index=True)
#     orf_class = db.Column(db.String, nullable=True, index=True)
#     subclass = db.Column(db.String, nullable=True, index=True)
#     target = db.Column(db.String, nullable=True, index=True)

#     def serialize(self):
#        """Return object data in easily serializable format"""
#        return {
#            'id': "",
#            'orf_name': self.orf_name,
#            'orf_class': self.orf_class,
#            'subclass': self.subclass,
#            'target': self.target,
#            'accession': self.accession,
#            'name': self.name,
#            'organism': self.organism,
#            'country': self.country
#        }


class Orf_Summary(db.Model):
    __tablename__ = "orf_summary"
    id = db.Column(db.Integer, nullable=False, primary_key=True)
    orf_name = db.Column(db.String, nullable=False, index=True)
    orf_class = db.Column(db.String, nullable=True, index=True)
    subclass = db.Column(db.String, nullable=True, index=True)
    target = db.Column(db.String, nullable=True, index=True)

    entries = db.relationship(
        "Entry_Orf_Summary",
        backref="entry_orf",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            "id": self.id,
            "orf_name": self.orf_name,
            "orf_class": self.orf_class,
            "subclass": self.subclass,
            "target": self.target,
        }


class Entry_Orf_Summary(db.Model):
    __tablename__ = "entry_orf_summary"
    id = db.Column(db.Integer, nullable=False, primary_key=True)
    entry_id = db.Column(db.Integer, nullable=False, index=True)
    summary_id = db.Column(
        db.Integer, db.ForeignKey("orf_summary.id", ondelete="CASCADE"), nullable=False
    )
    accession = db.Column(db.String(100), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    organism = db.Column(db.String(250), nullable=True)
    country = db.Column(db.String(50), nullable=True)

    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            "id": "",
            "accession": self.accession,
            "name": self.name,
            "organism": self.organism,
            "country": self.country,
        }


class User(db.Model, UserMixin):
    __tablename__ = "user"
    user_id = db.Column(db.Integer, primary_key=True, nullable=False)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(102), nullable=False)

    genbanks = db.relationship(
        "UserGenbank", backref="user_gb", lazy="dynamic", cascade="all, delete-orphan"
    )
    change_logs = db.relationship(
        "ChangeLog", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __init__(self, username, password):
        self.username = username
        self.password = generate_password_hash(password)

    def set_password(self, passwd):
        self.password = generate_password_hash(passwd)

    def get_id(self):
        return self.user_id


class UserGenbank(db.Model):
    __tablename__ = "user_gb"
    gb_id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    entry_id = db.Column(
        db.Integer,
        db.ForeignKey("te_entry.entry_id", ondelete="CASCADE"),
        nullable=False,
    )

    file_size = db.Column(db.Integer, nullable=False)
    upload_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    qc_time = db.Column(db.DateTime, nullable=True)

    image_name = db.Column(db.String(50), nullable=True)
    image_size = db.Column(db.Integer, nullable=True)
    image_time = db.Column(db.DateTime, nullable=True)  # when the file was uploaded

    snap_name = db.Column(db.String(50), nullable=True)
    snap_size = db.Column(db.Integer, nullable=True)
    snap_time = db.Column(db.DateTime, nullable=True)  # when the file was uploaded

    # image_name = db.Column(db.String(50), nullable=True)
    filename = db.Column(db.String(50), nullable=False)
    accession = db.Column(db.String(50), nullable=False)

    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            # "select": "",
            "id": self.gb_id,
            # "select": "",
            "accession": self.te_entry.accession,
            "filename": self.filename,
            "filesize": self.file_size,
            "upload_time": self.upload_time,
            "qc_time": self.qc_time,
        }

    def datatable(self):
        """Return object data in easily serializable format"""
        return {
            "select": "",
            "accession": self.te_entry.accession,
            "filename": self.filename,
            "filesize": self.file_size,
            "upload_time": self.upload_time,
            "qc_time": self.qc_time,
        }


class External_Resource(db.Model):
    __tablename__ = "external_resource"
    external_id = db.Column(db.Integer, primary_key=True, nullable=False)
    database_name = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.String(50), nullable=False)

    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            "id": self.external_id,
            "database_name": self.database_name,
            "resource_id": self.resource_id,
        }

    def datatable(self):
        """Return object data in easily serializable format"""
        return {"select": "", "resource_id": self.resource_id, "btn_fasta": ""}


class ChangeLog(db.Model):
    __tablename__ = "change_log"
    log_id = db.Column(db.Integer, primary_key=True, nullable=False)
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("upload_category.category_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    time_changed = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    filename = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(250), nullable=True)

    
    def username(self):
        return self.user.username
    
    def category_name(self):
        return self.category.category_name

    def datatable(self):
        """Return object data in easily serializable format"""
        filename = self.filename
        f_cols = filename.split("/")
        filename = f_cols[-1]
        return {
            "select": "",
            "filename": filename,
            "time_changed": self.time_changed,
            "action": self.action,
            "user": self.user.username,
            "category": self.category.category_name
        }


class UploadCategory(db.Model):
    __tablename__ = "upload_category"
    category_id = db.Column(db.Integer, primary_key=True, nullable=False)
    category_name = db.Column(db.String(50), nullable=False)

    change_logs = db.relationship(
        "ChangeLog", backref="category", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __init__(self, category):
        self.category_name = category


# import enum
# from sqlalchemy import Enum

# class EnumParameterType(enum.Enum):
#     TEXT = 1
#     NUMBER = 2

# class Job_Param(db.Model):
#     __tablename__ = "job_parameter"
#     job_param_id = db.Column(db.Integer, primary_key=True, nullable=False)
#     param_name = db.Column(db.String(50), nullable=False)
#     param_value = db.Column(db.String(50), nullable=False)
#     param_type = db.Column(db.Enum(EnumParameterType), nullable=False)

#     def serialize(self):
#         """Return object data in easily serializable format"""
#         return {
#             "id": self.job_param_id,
#             "param_name": self.param_name,
#             "param_value": self.param_value,
#             "param_type": self.param_type
#         }
#     def datatable(self):
#         """Return object data in easily serializable format"""
#         return {
#             "id": self.job_param_id,
#             "param_name": self.param_name,
#             "param_value": self.param_value,
#             "param_type": self.param_type
#         }
