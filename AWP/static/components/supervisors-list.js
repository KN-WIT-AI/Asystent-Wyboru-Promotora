function SupervisorsList(supervisors) {
  return new ComponentBuilder("div")
    .withChild(new H2Builder("Najlepsze dopasowania:").build())
    .withChild(
      supervisors.map((supervisor, index) =>
        SupervisorCard(index + 1, supervisor)
      )
    )
    .build();
}
