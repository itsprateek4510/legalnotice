/** @jest-environment node */
import { renderToStaticMarkup } from "react-dom/server";
import ResultCard from "./ResultCard";

describe("ResultCard", () => {
  test("renders title and child content with default styling", () => {
    const html = renderToStaticMarkup(<ResultCard title="Summary"><p>Demo notice</p></ResultCard>);
    expect(html).toContain('<h2 class="card-title">Summary</h2>');
    expect(html).toContain('<div class="card-body"><p>Demo notice</p></div>');
    expect(html).toContain('class="card card-default"');
    expect(html).not.toContain('class="card-icon"');
  });

  test("renders warning tone and decorative icon", () => {
    const html = renderToStaticMarkup(<ResultCard title="Warning" icon="!" tone="warning">Do not ignore</ResultCard>);
    expect(html).toContain('class="card card-warning"');
    expect(html).toContain('<span class="card-icon" aria-hidden="true">!</span>');
    expect(html).toContain('<div class="card-body">Do not ignore</div>');
  });
});
