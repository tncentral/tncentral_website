# on the server check if the service is active using:
# systemctl status tnworker.service
import os

# https://python-rq.org/docs/
import redis
from rq import Worker, Queue, Connection
import worker_settings

queues = worker_settings.QUEUES.copy()
redis_url = worker_settings.REDIS_URL

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, queues)))
        worker.work(with_scheduler=True)

def delete_jobs(registry, job_id="", check_expired=True):
    all_jobs = registry.get_job_ids()
    for job in all_jobs:
        if job_id == "" or job == job_id:
            registry.remove(job, delete_job=True)
    if check_expired:
        expired_failed_jobs = registry.get_expired_job_ids()
        for failed_expired in expired_failed_jobs:
            if job_id == "" or failed_expired == job_id:
                registry.remove(failed_expired, delete_job=True)

def delete_all_jobs(queue="default"):
    queue = Queue(queue, connection=conn)
    delete_jobs(queue.canceled_job_registry, check_expired=False)
    delete_jobs(queue.deferred_job_registry)
    delete_jobs(queue.started_job_registry)
    delete_jobs(queue.failed_job_registry)
    delete_jobs(queue.finished_job_registry)
    delete_jobs(queue.scheduled_job_registry, check_expired=False)
    

def get_jobs(registry):
    jobs = registry.get_job_ids()
    expired_jobs = registry.get_expired_job_ids()
    list_jobs = []
    for job in jobs:
        list_jobs.append(job)
    for expired_job in expired_jobs:
        list_jobs.append(expired_job)
    return list_jobs


def get_all_jobs(queue="default"):
    queue = Queue(queue, connection=conn)
    list_jobs = []
    list_jobs.extend(get_jobs(queue.started_job_registry))
    list_jobs.extend(get_jobs(queue.finished_job_registry))
    list_jobs.extend(get_jobs(queue.failed_job_registry))
    list_jobs.extend(get_jobs(queue.scheduled_job_registry))
    list_jobs.extend(get_jobs(queue.deferred_job_registry))
    return list_jobs