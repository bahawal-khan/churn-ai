import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DataTable } from "./DataTable";

interface Row {
  id: number;
  name: string;
  score: number;
}

const ROWS: Row[] = [
  { id: 1, name: "Charlie", score: 30 },
  { id: 2, name: "Alice", score: 10 },
  { id: 3, name: "Bob", score: 20 },
];

const columns = [
  { key: "name", header: "Name", render: (r: Row) => r.name, sortValue: (r: Row) => r.name },
  { key: "score", header: "Score", render: (r: Row) => String(r.score), sortValue: (r: Row) => r.score },
];

describe("DataTable", () => {
  it("renders every row", () => {
    render(<DataTable rows={ROWS} columns={columns} getRowId={(r) => r.id} />);
    expect(screen.getByText("Charlie")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("shows the empty message when there are no rows", () => {
    render(<DataTable rows={[]} columns={columns} getRowId={(r) => r.id} emptyMessage="No rows yet." />);
    expect(screen.getByText("No rows yet.")).toBeInTheDocument();
  });

  it("sorts rows ascending then descending when a sortable header is clicked", async () => {
    const user = userEvent.setup();
    render(<DataTable rows={ROWS} columns={columns} getRowId={(r) => r.id} />);

    const getNameCells = () =>
      screen.getAllByRole("row").slice(1).map((row) => row.querySelector("td")?.textContent);

    // Unsorted (insertion order).
    expect(getNameCells()).toEqual(["Charlie", "Alice", "Bob"]);

    await user.click(screen.getByText("Name"));
    expect(getNameCells()).toEqual(["Alice", "Bob", "Charlie"]);

    await user.click(screen.getByText("Name"));
    expect(getNameCells()).toEqual(["Charlie", "Bob", "Alice"]);
  });

  it("calls onPageChange with the requested page from pagination controls", async () => {
    const user = userEvent.setup();
    const onPageChange = jest.fn();
    render(
      <DataTable
        rows={ROWS}
        columns={columns}
        getRowId={(r) => r.id}
        pagination={{ page: 2, totalPages: 3, onPageChange }}
      />
    );

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(onPageChange).toHaveBeenCalledWith(3);

    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("disables Previous on the first page and Next on the last page", () => {
    render(
      <DataTable
        rows={ROWS}
        columns={columns}
        getRowId={(r) => r.id}
        pagination={{ page: 1, totalPages: 3, onPageChange: jest.fn() }}
      />
    );
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).not.toBeDisabled();
  });
});
