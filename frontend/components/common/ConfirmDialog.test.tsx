import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ConfirmDialog } from "./ConfirmDialog";

describe("ConfirmDialog", () => {
  it("does not call onConfirm until the user explicitly confirms", async () => {
    const user = userEvent.setup();
    const onConfirm = jest.fn();
    const onClose = jest.fn();

    render(
      <ConfirmDialog
        open
        onClose={onClose}
        onConfirm={onConfirm}
        title="Deactivate this model?"
        description="This will fall back to the baseline model."
        confirmLabel="Deactivate"
        danger
      />
    );

    expect(onConfirm).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Deactivate" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("cancels without calling onConfirm", async () => {
    const user = userEvent.setup();
    const onConfirm = jest.fn();
    const onClose = jest.fn();

    render(
      <ConfirmDialog
        open
        onClose={onClose}
        onConfirm={onConfirm}
        title="Delete this dataset?"
        description="This cannot be undone."
      />
    );

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders nothing destructive when closed", () => {
    render(
      <ConfirmDialog
        open={false}
        onClose={jest.fn()}
        onConfirm={jest.fn()}
        title="Delete this dataset?"
        description="This cannot be undone."
      />
    );
    expect(screen.queryByText("Delete this dataset?")).not.toBeInTheDocument();
  });
});
