int has_cycle(list l) {
  list p = l;
  list q = l;

  do {
    // Go twice as fast!
    if (p != NULL) p = p->n;
    if (p != NULL) p = p->n;

    if (q != NULL) q = q->n;
    if (q != NULL) q = q->n;
    if (q != NULL) q = q->n;
    if (q != NULL) q = q->n;
  } while (p ! q && p != NULL && q != NULL);

  return p == q;
}
