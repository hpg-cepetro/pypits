/*
 *  spitz.h
 *
 *  Copyright (C) 2015 Caian Benedicto <caian@ggaunicamp.com>
 *
 *  This file is part of Spitz
 *
 *  Spitz is free software; you can redistribute it and/or modify it
 *  under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2, or (at your option)
 *  any later version.
 *
 *  Spitz is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 */

 /* Python version of spits use cdecl calling convention */

#if defined(__GNUC__)
#define __cdecl __attribute__((__cdecl__))
#endif

/* The size used to pass messages is 64 bit */

typedef long long int spitzsize_t;

/* Runner callback that executes the task distribution and committing */

typedef int (*runner_t)(int, const char **, const void**, spitzsize_t*);

/* Spits main */

int __cdecl spits_main(int argc, const char* argv[], runner_t runner);

/* Job Manager */

void* __cdecl spits_job_manager_new(int argc, const char *argv[]);

int __cdecl spits_job_manager_next_task(void *user_data, const void** task,
    spitzsize_t* tasksz);

int __cdecl spits_job_manager_finalize(void *user_data);

/* Worker */

void* __cdecl spits_worker_new(int argc, const char *argv[]);

int __cdecl spits_worker_run(void *user_data, const void* task,
    spitzsize_t tasksz, const void** result, spitzsize_t* resultsz);

int __cdecl spits_worker_finalize(void *user_data);

/* Committer */

void* __cdecl spits_committer_new(int argc, const char *argv[]);

int __cdecl spits_committer_commit_pit(void *user_data,
    const void* result, spitzsize_t resultsz);

int __cdecl spits_committer_commit_job(void *user_data,
    const void** final_result, spitzsize_t* final_resultsz);

int __cdecl spits_committer_finalize(void *user_data);
