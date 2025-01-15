function SupervisorCard(index, supervisor) {
  const supervisorDiv = new ComponentBuilder("div")
    .withClass("supervisor-result")
    .withChild(new H3Builder(`#${index} ${supervisor.supervisor}`).build())
    .withChild(
      new ParagraphBuilder(
        `Średnia odległość: ${Number.parseFloat(supervisor.average_score).toFixed(4)}`
      ).build()
    );

  if (supervisor.top_interests.length > 0) {
    supervisorDiv.withChild(
      HeaderedList(
        "Dopasowane zainteresowania:",
        supervisor.top_interests
      )
    );
  }

  if (supervisor.top_papers.length > 0) {
    supervisorDiv.withChild(
      HeaderedList("Dopasowane prace:", supervisor.top_papers)
    );
  }

  return supervisorDiv.build();
}
