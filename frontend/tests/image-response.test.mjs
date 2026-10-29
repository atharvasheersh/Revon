import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { ImageResponse } from "vinext/shims/og";

test("the framework image response renders a PNG with the patched OG library", async () => {
  const response = new ImageResponse(
    createElement("div", {
      style: {
        display: "flex",
        width: "100%",
        height: "100%",
        alignItems: "center",
        justifyContent: "center",
        background: "white",
        color: "black",
        fontSize: 32,
      },
    }, "Revon"),
    { width: 320, height: 160, status: 201, headers: { "x-revon-image": "test" } },
  );

  assert.equal(response.status, 201);
  assert.equal(response.headers.get("content-type"), "image/png");
  assert.equal(response.headers.get("x-revon-image"), "test");
  const image = Buffer.from(await response.arrayBuffer());
  assert.deepEqual([...image.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  assert.equal(image.readUInt32BE(16), 320);
  assert.equal(image.readUInt32BE(20), 160);
});
