from datetime import datetime
from rq.job import Job
from rq.exceptions import NoSuchJobError
import worker
import os

FORMAT_TIME="%m/%d/%Y %H:%M:%S"


class TnJob:
    def __init__(self, jobId):
        self.__jobId=jobId
    
    def get_id(self):
        return self.__jobId
    
    @property
    def enqueued_at(self) -> datetime:
        return self.__enqueued_at 
    
    @enqueued_at.setter
    def enqueued_at(self, enqueued_at:datetime):
        self.__enqueued_at=enqueued_at
    
    @property
    def started_at(self) -> datetime:
        return self.__started_at
    
    @started_at.setter
    def started_at(self, started_at:datetime):
        self.__started_at=started_at
    
    @property
    def ended_at(self) -> datetime:
        return self.__ended_at
    
    @ended_at.setter
    def ended_at(self, ended_at:datetime):
        self.__ended_at=ended_at

    @property
    def is_failed(self) -> bool:
        return self.__is_failed
    
    @is_failed.setter
    def is_failed(self, is_failed:bool):
        self.__is_failed=is_failed

    @property
    def is_finished(self) -> bool:
        return self.__is_finished
    
    @is_finished.setter
    def is_finished(self, is_finished:bool):
        self.__is_finished=is_finished
    
    @property
    def is_canceled(self) -> bool:
        return False
    @property
    def is_deferred(self) -> bool:
        return False
    @property
    def is_queued(self) -> bool:
        return False
    @property
    def is_scheduled(self) -> bool:
        return False
    @property
    def is_started(self) -> bool:
        return False
    @property
    def is_stopped(self) -> bool:
        return False

class JobWrapper:
    def __init__(self, rqJob:Job=None, tnJob:TnJob=None, fileSize=0):
        self.__rq_job = rqJob
        self.__tn_job = tnJob
        self.__file_size = fileSize

    def __get_job(self):
        job = self.__tn_job
        if self.__rq_job:
            job = self.__rq_job
        return job
    @property
    def jobId(self) -> str:
        return self.__get_job().get_id()

    @property
    def fileSize(self) -> float:
        return self.__file_size
    
    @fileSize.setter
    def fileSize(self, fileSize:float):
        self.__file_size=fileSize
    
    @property
    def enqueued_at(self) -> datetime:
        return self.__get_job().enqueued_at
    
    @property
    def started_at(self) -> datetime:
        return self.__get_job().started_at
    
    @property
    def ended_at(self) -> datetime:
        return self.__get_job().ended_at
    
    
    @property
    def sorted_enqueued_at(self) -> float:
        if self.enqueued_at:
            return self.enqueued_at.timestamp()
        return self.started_at.max.timestamp()
    @property
    def sorted_started_at(self) -> float:
        if self.started_at:
            return self.started_at.timestamp()
        return self.started_at.max.timestamp()
    
    @property
    def sorted_ended_at(self) -> float:
        if self.ended_at:
            return self.ended_at.timestamp()
        return self.started_at.max.timestamp()
    
    @property
    def status(self) -> str:
        return_status = ""
        job = self.__get_job()

        if job.is_canceled:
            return_status = "Canceled"
        elif job.is_deferred:
            return_status = "Deferred"
        elif job.is_failed:
            return_status = "Failed"
        elif job.is_finished:
            return_status = "Finished"
        elif job.is_queued:
            return_status = "Enqueued"
        elif job.is_scheduled:
            return_status = "Scheduled"
        elif job.is_started:
            return_status = "Running"
        elif job.is_stopped:
            return_status = "Stopped"
        else:
            return_status = "Undefined"
        return return_status
   
    
    def asStr(self, value:datetime):
        if value:
            return value.strftime(FORMAT_TIME)
        else:
            return ""
    
    def sortEnqueuedAt(self, other:Job): # like __lt__ 

        if other.enqueued_at and self.__get_job().enqueued_at:
            if self.__get_job().enqueued_at < other.enqueued_at:
                return True
            
        return False
    
    def exec_time(self):
        return_value = ""
        if self.rqJob.ended_at:
            ex_time = self.rqJob.ended_at-self.rqJob.started_at
            if ex_time.seconds > 60:
                in_minutes = ex_time.seconds / 60
                if in_minutes > 60:
                    in_hours = in_minutes / 60

                    return_value = f"{in_hours} hour(s)"
                else:
                    return_value = f"{in_minutes} second(s)"
            else:
                return_value = f"{ex_time.seconds} second(s)"
        return return_value
    
    def search(self, text) -> bool:
        if self.jobId.lower().find(text.lower()) != -1:
            return True
        if self.enqueuedAt.lower().find(text.lower()) != -1:
            return True
        if self.startedAt.lower().find(text.lower()) != -1:
            return True
        if self.endedAt.lower().find(text.lower()) != -1:
            return True
        if self.status.lower().find(text.lower()) != -1:
            return True
        return False
    
    def datatable(self):
        if self.fileSize > 1000:
            fileSize = self.fileSize/1000
            sizeText = f"{fileSize:.2f} MB"
        else:
            sizeText = f"{self.fileSize:.2f} KB"
        return {
            "job_id": self.jobId,
            "status": self.status,
            "file_size": sizeText,
            "enqueued_at": self.asStr(self.__get_job().enqueued_at),
            "started_at": self.asStr(self.__get_job().started_at),
            "ended_at": self.asStr(self.__get_job().ended_at),
            "buttons": ""
        }

def tnjob_from_info(jobId, filepath):
    tnJob = TnJob(jobId)
    with open(filepath, "r") as reader:
        for line in reader.readlines():
            line = line.strip("\n")
            cols = line.split("\t")
            if cols[0].startswith("Enqueued"):
                t = datetime.strptime(cols[1], FORMAT_TIME)
                tnJob.enqueued_at = t
            elif cols[0].startswith("Started"):
                t = datetime.strptime(cols[1], FORMAT_TIME)
                tnJob.started_at = t
            elif cols[0].startswith("Ended"):
                t = datetime.strptime(cols[1], FORMAT_TIME)
                tnJob.ended_at = t
    return tnJob

def get_jobs_from_dir(jobs_dir):
    list_dir = os.listdir(jobs_dir)
    all_jobs = []
    for job_dir in list_dir:
        rq_job = None
        tn_job = None
        try:
            rq_job = Job.fetch(job_dir, worker.conn)
        except NoSuchJobError:
            filepath = os.path.join(jobs_dir, job_dir, job_dir+".info")
            tn_job = tnjob_from_info(job_dir, filepath)
            errorpath = os.path.join(jobs_dir, job_dir, job_dir+".error")
            outpath = os.path.join(jobs_dir, job_dir, job_dir+".fa.out")
            if os.path.exists(errorpath):
                tn_job.is_failed=True
                tn_job.is_finished=False
            else:
                size_out = os.path.getsize(outpath)
                if size_out > 300:
                    tn_job.is_finished=True
                    tn_job.is_failed=False
                else:
                    tn_job.is_finished=False
                    tn_job.is_failed=False
        query_filename=os.path.join(jobs_dir, job_dir, job_dir+".fa")
        size_kb = os.path.getsize(query_filename) / 1000
        job_wrapper = JobWrapper(rq_job, tn_job, fileSize=size_kb)
        all_jobs.append(job_wrapper)
    return all_jobs