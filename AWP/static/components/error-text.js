function ErrorText(error) {
  return new ParagraphBuilder(error).withClass("error").build();
}
