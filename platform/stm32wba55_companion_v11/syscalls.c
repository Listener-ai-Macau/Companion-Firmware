/* Diagnostic uses bounded snprintf and explicit UART output, no POSIX I/O or
 * heap. Defining these makes accidental libc I/O/allocation fail explicitly. */
#include <errno.h>
#include <stddef.h>
#include <sys/stat.h>
int _fstat(int fd, struct stat *status) { (void)fd; (void)status; errno = EBADF; return -1; }
int _isatty(int fd) { (void)fd; errno = EBADF; return 0; }
int _close(int fd) { (void)fd; errno = EBADF; return -1; }
int _lseek(int fd, int offset, int whence) { (void)fd; (void)offset; (void)whence; errno = ESPIPE; return -1; }
int _read(int fd, char *data, int size) { (void)fd; (void)data; (void)size; errno = ENOSYS; return -1; }
int _write(int fd, const char *data, int size) { (void)fd; (void)data; (void)size; errno = ENOSYS; return -1; }
void *_sbrk(ptrdiff_t increment) { (void)increment; errno = ENOMEM; return (void *)-1; }
