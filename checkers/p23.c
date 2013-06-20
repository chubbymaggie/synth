int check(unsigned int x, unsigned int z) {
  int cnt = 0;

  for (int i = 0; i < 32; i++) {
    if (x & 1) {
      cnt++;
    }

    x >>= 1;
  }

  return cnt == z;
}
