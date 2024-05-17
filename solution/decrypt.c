#include <assert.h>
#include <stdio.h>
#include <malloc.h>
#include <stdint.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <error.h>

#define N_WORDS 1024
#define N_BYTES (N_WORDS << 2)
#define N_INPUT_BYTES (N_BYTES / 4 * 3)
#include "enc_key.h"

static const unsigned char pr2six[256] =
{
    /* ASCII table */
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 62, 64, 64, 64, 63,
    52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 64, 64, 64, 64, 64, 64,
    64,  0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14,
    15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 64, 64, 64, 64, 64,
    64, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
    41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64
};

int Base64decode_len(const char *bufcoded)
{
    int nbytesdecoded;
    register const unsigned char *bufin;
    register int nprbytes;

    bufin = (const unsigned char *) bufcoded;
    while (pr2six[*(bufin++)] <= 63);

    nprbytes = (bufin - (const unsigned char *) bufcoded) - 1;
    nbytesdecoded = ((nprbytes + 3) / 4) * 3;

    return nbytesdecoded + 1;
}

int Base64decode(char *bufplain, const char *bufcoded)
{
    int nbytesdecoded;
    register const unsigned char *bufin;
    register unsigned char *bufout;
    register int nprbytes;

    bufin = (const unsigned char *) bufcoded;
    while (pr2six[*(bufin++)] <= 63);
    nprbytes = (bufin - (const unsigned char *) bufcoded) - 1;
    nbytesdecoded = ((nprbytes + 3) / 4) * 3;

    bufout = (unsigned char *) bufplain;
    bufin = (const unsigned char *) bufcoded;

    while (nprbytes > 4) {
    *(bufout++) =
        (unsigned char) (pr2six[*bufin] << 2 | pr2six[bufin[1]] >> 4);
    *(bufout++) =
        (unsigned char) (pr2six[bufin[1]] << 4 | pr2six[bufin[2]] >> 2);
    *(bufout++) =
        (unsigned char) (pr2six[bufin[2]] << 6 | pr2six[bufin[3]]);
    bufin += 4;
    nprbytes -= 4;
    }

    /* Note: (nprbytes == 1) would be an error, so just ingore that case */
    if (nprbytes > 1) {
    *(bufout++) =
        (unsigned char) (pr2six[*bufin] << 2 | pr2six[bufin[1]] >> 4);
    }
    if (nprbytes > 2) {
    *(bufout++) =
        (unsigned char) (pr2six[bufin[1]] << 4 | pr2six[bufin[2]] >> 2);
    }
    if (nprbytes > 3) {
    *(bufout++) =
        (unsigned char) (pr2six[bufin[2]] << 6 | pr2six[bufin[3]]);
    }

    *(bufout++) = '\0';
    nbytesdecoded -= (4 - nprbytes) & 3;
    return nbytesdecoded;
}

// special case for mod inverse in 2**32
// https://jeffhurchalla.com/2022/04/25/a-faster-multiplicative-inverse-mod-a-power-of-2/
uint32_t multiplicative_inverse(uint32_t a) {
    assert(a%2 == 1);  // the inverse (mod 2**32) only exists for odd values
    uint32_t x0 = (3*a)^2;
    uint32_t y = 1 - a*x0;
    uint32_t x1 = x0*(1 + y);
    y *= y;
    uint32_t x2 = x1*(1 + y);
    y *= y;
    uint32_t x3 = x2*(1 + y);
    return x3;
}

uint32_t bitreverse_i32(uint32_t val) {
    /* swap odd/even bits */
    val = ((val >> 1) & 0x55555555) | ((val & 0x55555555) << 1);

    /* swap consecutive bit pairs */
    val = ((val >> 2) & 0x33333333) | ((val & 0x33333333) << 2);

    /* swap consecutive nibbles */
    val = ((val >> 4) & 0x0f0f0f0f) | ((val & 0x0f0f0f0f) << 4);

    /* swap consecutive bytes */
    val = ((val >> 8) & 0x00ff00ff) | ((val & 0x00ff00ff) << 8);

    /* swap shorts */
    return (val >> 16) | (val << 16);
}

uint32_t bitrev_add(uint32_t a, uint32_t b) {
    return bitreverse_i32(bitreverse_i32(a) + bitreverse_i32(b));
}

uint32_t bitrev_sub(uint32_t a, uint32_t b) {
    return bitreverse_i32(bitreverse_i32(a) - bitreverse_i32(b));
}

typedef struct {
    uint8_t r;
    uint8_t i;
} Complex;

typedef Complex CMulMap[128][128][256][256];

Complex cmul(Complex a, Complex b) {
    Complex res;
    res.r = a.r * b.r - a.i * b.i;
    res.i = a.r * b.i + a.i * b.r;
    return res;
}

// Create a map from key+output back to input
CMulMap *gen_cmul_map() {
    CMulMap *map = malloc(128L * 128 * 256 * 256 * sizeof(Complex));
    if (map == NULL) {
        return NULL;
    }
    Complex in, out, key;

    // per construction all key bytes are odd
    for (int i1 = 1; i1 < 256; i1+=2) {
        key.r = i1;
        for (int i2 = 1; i2 < 256; i2+=2) {
            key.i = i2;
            // because the input is base64 encoded all input bytes must be smaller than 128
            for (int i3 = 0; i3 < 128; i3++) {
                in.r = i3;
                for (int i4 = 0; i4 < 128; i4++) {
                    in.i = i4;
                    out = cmul(in, key);
                    //printf("%02x %02x %02x %02x %02x %02x\n", in.r, in.i, out.r, out.i, key.r, key.i);
                    (*map)[key.r>>1][key.i>>1][out.r][out.i] = in;
                }
            }
        }
    }
    return map;
}

Complex extract_c(uint32_t val, int top) {
    Complex res;
    res.r = (val >> (top ? 24 : 16)) & 0xff;
    res.i = (val >> (top ? 8 : 0)) & 0xff;
    return res;
}

uint32_t pack_c(Complex lower, Complex upper) {
    return lower.i | upper.i << 8 | lower.r << 16 | upper.r << 24;
}

void decrypt(CMulMap *map, uint32_t *src, uint32_t *dst) {
    uint8_t *b_src = (uint8_t*)src;
    uint8_t *b_dst = (uint8_t*)dst;
    uint32_t bitrev_offset = 0;

    // init bitref offset
    for (int i = 0; i < 19; i++) {
        bitrev_offset = bitrev_add(bitrev_offset, 0x800);
    }

    // round function: invert multiplication and bitrev shuffling
    for (int round = 0; round < 20; round++) {
        for (int i = 0; i < N_WORDS; i++) {
            src[i] = dst[i] * multiplicative_inverse(enc_key[i]);
        }

        for (int i = 0; i < N_BYTES; i++) {
            b_dst[i] = b_src[bitrev_offset];
            bitrev_offset = bitrev_add(bitrev_offset, 0x800);
        }

        bitrev_offset = bitrev_sub(bitrev_offset, 0x800);
    }

    for (int i = 0; i < N_WORDS; i++) {
        Complex lower, upper, num, key;
        key = extract_c(enc_key[i], 0);
        num = extract_c(dst[i], 0);
        lower = (*map)[key.r>>1][key.i>>1][num.r][num.i];
        key = extract_c(enc_key[i], 1);
        num = extract_c(dst[i], 1);
        upper = (*map)[key.r>>1][key.i>>1][num.r][num.i];
        src[i] = pack_c(lower, upper);
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: <encrypted file> <decrypted file>\n");
        return -1;
    }
    int enc_file = open(argv[1], O_RDONLY);
    if (enc_file < 0) {
        perror("Open encypted file");
        return -1;
    }
    int dec_file = open(argv[2], O_RDWR | O_CREAT | O_TRUNC, S_IRUSR|S_IWUSR);
    if (dec_file < 0) {
        perror("Open decrypted file");
        return -1;
    }

    uint32_t *src = malloc(N_BYTES+1);
    uint32_t *dst = malloc(N_BYTES);
    if (src == NULL || dst == NULL) {
        printf("Couldn't allocate memory for src|dst\n");
        return -1;
    }

    printf("Generating cmul map. This might take a moment.\n");
    CMulMap *map = gen_cmul_map();
    if (map == NULL) {
        printf("Couldn't allocate memory for cmul map\n");
        return -1;
    }
    printf("Generating done. Decrypting data.\n");


    int ret;
    do {
        ret = read(enc_file, dst, N_BYTES);
        if (ret == -1) {
            perror("Reading encrypted data");
            return -1;
        } else if (ret == 0) {
            break;
        }

        decrypt(map, src, dst);
        int n_decoded = Base64decode((char*)dst, (char*)src);

        int n_written = write(dec_file, dst, n_decoded);
        assert(n_written == n_decoded);
    } while (ret == N_BYTES);

    free(map);
    free(src);
    free(dst);

    return 0;
}
