import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { UploadDropzone } from "./UploadDropzone";

function makeFile(name: string, sizeBytes: number, type = "text/csv"): File {
  const file = new File(["a".repeat(Math.min(sizeBytes, 10))], name, { type });
  Object.defineProperty(file, "size", { value: sizeBytes });
  return file;
}

async function selectFile(file: File) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  const user = userEvent.setup();
  await user.upload(input, file);
}

// `userEvent.upload` respects the input's `accept=".csv"` attribute and
// silently skips files that don't match it — this test is specifically
// about the component's *own* client-side validation catching a wrong
// extension, so it dispatches the change event directly to bypass that
// browser-level filtering (a user could still rename a file to `.csv`).
function selectFileBypassingAccept(file: File) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  Object.defineProperty(input, "files", { value: [file], configurable: true });
  fireEvent.change(input);
}

describe("UploadDropzone", () => {
  it("rejects a non-.csv file client-side without calling onUpload", async () => {
    const onUpload = jest.fn();
    const onSuccess = jest.fn();
    render(<UploadDropzone onUpload={onUpload} onSuccess={onSuccess} />);

    selectFileBypassingAccept(makeFile("customers.xlsx", 1024));

    expect(await screen.findByText(/only \.csv files are supported/i)).toBeInTheDocument();
    expect(onUpload).not.toHaveBeenCalled();
  });

  it("rejects an oversized file client-side without calling onUpload", async () => {
    const onUpload = jest.fn();
    const onSuccess = jest.fn();
    render(<UploadDropzone onUpload={onUpload} onSuccess={onSuccess} />);

    await selectFile(makeFile("huge.csv", 26 * 1024 * 1024));

    expect(await screen.findByText(/too large/i)).toBeInTheDocument();
    expect(onUpload).not.toHaveBeenCalled();
  });

  it("rejects an empty file client-side", async () => {
    const onUpload = jest.fn();
    render(<UploadDropzone onUpload={onUpload} onSuccess={jest.fn()} />);

    await selectFile(makeFile("empty.csv", 0));

    expect(await screen.findByText(/this file is empty/i)).toBeInTheDocument();
    expect(onUpload).not.toHaveBeenCalled();
  });

  it("uploads a valid .csv file and calls onSuccess with the result", async () => {
    const onUpload = jest.fn().mockResolvedValue({ ok: true });
    const onSuccess = jest.fn();
    render(<UploadDropzone onUpload={onUpload} onSuccess={onSuccess} />);

    await selectFile(makeFile("customers.csv", 2048));

    expect(onUpload).toHaveBeenCalledTimes(1);
    await screen.findByText(/drag & drop/i); // dropzone re-renders after upload settles
    expect(onSuccess).toHaveBeenCalledWith({ ok: true }, expect.any(File));
  });

  it("shows a retry affordance when the upload itself fails", async () => {
    const { ApiError } = await import("@/lib/api/client");
    const onUpload = jest.fn().mockRejectedValue(new ApiError({ code: "INTERNAL_ERROR", message: "Upload failed on the server.", details: {} }, 500, null));
    render(<UploadDropzone onUpload={onUpload} onSuccess={jest.fn()} />);

    await selectFile(makeFile("customers.csv", 2048));

    expect(await screen.findByText("Upload failed on the server.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
