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

#ifndef __SPITZ_H__
#define __SPITZ_H__

#ifdef __cplusplus
extern "C" {
#endif

 /* Python version of spits uses cdecl calling convention */

/* The size used to pass messages is 64 bit */

typedef long long int spitssize_t;

typedef const void* spitsctx_t;

/* Runner callback that executes the task distribution and committing */

typedef int (*spitzrun_t)(int, const char**, const void**, spitssize_t*);

/* Pusher callback that performs result submission from a worker */

typedef void (*spitspush_t)(const void*, spitssize_t, spitsctx_t);

/* Spits main */

int spits_main(int argc, const char* argv[], spitzrun_t run);

/* Job Manager */

void* spits_job_manager_new(int argc, const char *argv[]);

int spits_job_manager_next_task(void *user_data, 
    spitspush_t push_task, spitsctx_t jmctx);

void spits_job_manager_finalize(void *user_data);

/* Worker */

void* spits_worker_new(int argc, const char *argv[]);

int spits_worker_run(void *user_data, const void* task, 
    spitssize_t tasksz, spitspush_t push_result, 
    spitsctx_t taskctx);

void spits_worker_finalize(void *user_data);

/* Committer */

void* spits_committer_new(int argc, const char *argv[]);

int spits_committer_commit_pit(void *user_data,
    const void* result, spitssize_t resultsz);

int spits_committer_commit_job(void *user_data,
    spitspush_t push_final_result, spitsctx_t jobctx);

void spits_committer_finalize(void *user_data);

#ifdef __cplusplus
}
#endif

#endif /* __SPITZ_H__ */
