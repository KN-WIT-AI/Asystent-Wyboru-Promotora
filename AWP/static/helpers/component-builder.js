class ComponentBuilder {
  constructor(tag) {
    this.element = document.createElement(tag);
  }

  withClass(className) {
    this.element.classList.add(className);
    return this;
  }

  withChild(child) {
    if (Array.isArray(child)) {
      child.forEach((c) => this.element.appendChild(c));
      return this;
    }

    this.element.appendChild(child);
    return this;
  }

  withText(text) {
    this.element.innerText = text;
    return this;
  }

  build() {
    return this.element;
  }
}

class HeaderBuilder extends ComponentBuilder {
  constructor(size, text) {
    super(`h${size}`);
    this.withText(text);
  }
}

class H2Builder extends HeaderBuilder {
  constructor(text) {
    super(2, text);
  }
}

class H3Builder extends HeaderBuilder {
  constructor(text) {
    super(3, text);
  }
}

class H4Builder extends HeaderBuilder {
  constructor(text) {
    super(4, text);
  }
}

class UnorderedListBuilder extends ComponentBuilder {
  constructor(items) {
    super("ul");
    this.withChild(
      items.map((item) => new ComponentBuilder("li").withText(item).build())
    );
  }
}

class ParagraphBuilder extends ComponentBuilder {
  constructor(text) {
    super("p");
    this.withText(text);
  }
}