import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { formatCompact, formatValue, prettyColumnName } from "../utils/format";
import MessageBox from "./MessageBox";
import "./ChartView.css";

// Categorical colours, ALWAYS used in this order (series 1 = blue, 2 = orange, ...).
// The order is chosen so neighbouring colours stay distinguishable for
// colour-blind viewers - don't shuffle it. Hex values are needed here because
// SVG attributes can't read CSS variables.
const SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];

// Chart chrome: quiet greys so the data is the only loud thing.
const GRID_COLOR = "#e1e0d9";
const AXIS_COLOR = "#c3c2b7";
const SURFACE = "#ffffff";
const TICK_STYLE = { fill: "#5b6577", fontSize: 15 };

const CHART_HEIGHT = 420;
const LONG_LABEL = 12; // category names longer than this -> horizontal bars

/**
 * Draws the chart the backend suggested (result.chart = {type, x, y}).
 * The backend picks the type from the result's shape (see backend/app/chart.py);
 * this component only draws it.
 */
export default function ChartView({ chart, columns, rows }) {
  if (!chart || chart.type === "none" || !chart.x || !chart.y.length) {
    return (
      <MessageBox variant="info" title="No chart for this result">
        This answer doesn't have a shape that charts well (for example a single row, or no numbers to
        plot). The Result tab shows the full table.
      </MessageBox>
    );
  }

  // Recharts wants an array of objects: [{CityName: "Mumbai", Orders: 15794}, ...]
  const data = rows.map((row) => Object.fromEntries(columns.map((col, i) => [col, row[i]])));
  const title = `${chart.y.map(prettyColumnName).join(", ")} by ${prettyColumnName(chart.x)}`;

  // Tooltip: "₹5,68,027.95" instead of 568027.95, and readable series names.
  const tooltipFormatter = (value, name) => [formatValue(value, name), prettyColumnName(name)];
  const showLegend = chart.y.length >= 2; // one series needs no legend: the title names it

  return (
    <figure className="chart-view">
      <figcaption className="chart-view__title">{title}</figcaption>
      <ResponsiveContainer width="100%" height={chartHeight(chart, data)}>
        {chart.type === "line" ? renderLine(chart, data, tooltipFormatter, showLegend)
          : chart.type === "pie" ? renderPie(chart, data, tooltipFormatter)
          : renderBar(chart, data, tooltipFormatter, showLegend)}
      </ResponsiveContainer>
    </figure>
  );
}

function isHorizontalBar(chart, data) {
  return chart.type === "bar" && data.some((d) => String(d[chart.x]).length > LONG_LABEL);
}

function chartHeight(chart, data) {
  // Horizontal bars grow with the number of categories so labels never overlap.
  return isHorizontalBar(chart, data) ? Math.max(CHART_HEIGHT, data.length * 40 + 60) : CHART_HEIGHT;
}

function renderBar(chart, data, tooltipFormatter, showLegend) {
  const horizontal = isHorizontalBar(chart, data);
  // Long names (restaurants, riders) read better as horizontal bars with labels on the left.
  const categoryAxis = horizontal
    ? <YAxis type="category" dataKey={chart.x} width={230} tick={TICK_STYLE} stroke={AXIS_COLOR} interval={0} />
    : <XAxis dataKey={chart.x} tick={TICK_STYLE} stroke={AXIS_COLOR} interval={0} />;
  const valueAxis = horizontal
    ? <XAxis type="number" tickFormatter={formatCompact} tick={TICK_STYLE} stroke={AXIS_COLOR} />
    : <YAxis tickFormatter={formatCompact} tick={TICK_STYLE} stroke={AXIS_COLOR} width={70} />;

  return (
    <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"}
              margin={{ top: 10, right: 30, left: 10, bottom: 10 }} barGap={2}>
      <CartesianGrid stroke={GRID_COLOR} horizontal={!horizontal} vertical={horizontal} />
      {categoryAxis}
      {valueAxis}
      <Tooltip formatter={tooltipFormatter} cursor={{ fill: "rgba(42,120,214,0.08)" }} />
      {showLegend && <Legend formatter={prettyColumnName} />}
      {chart.y.map((column, i) => (
        <Bar key={column} dataKey={column} fill={SERIES_COLORS[i]} maxBarSize={24}
             // Rounded only at the data end; square where the bar meets the axis.
             radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} />
      ))}
    </BarChart>
  );
}

function renderLine(chart, data, tooltipFormatter, showLegend) {
  return (
    <LineChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
      <CartesianGrid stroke={GRID_COLOR} vertical={false} />
      <XAxis dataKey={chart.x} tick={TICK_STYLE} stroke={AXIS_COLOR} />
      <YAxis tickFormatter={formatCompact} tick={TICK_STYLE} stroke={AXIS_COLOR} width={70} />
      <Tooltip formatter={tooltipFormatter} />
      {showLegend && <Legend formatter={prettyColumnName} />}
      {chart.y.map((column, i) => (
        <Line key={column} type="linear" dataKey={column} stroke={SERIES_COLORS[i]} strokeWidth={2}
              // 8px dots with a white ring so they stay visible where lines cross.
              dot={{ r: 4, fill: SERIES_COLORS[i], stroke: SURFACE, strokeWidth: 2 }}
              activeDot={{ r: 6, stroke: SURFACE, strokeWidth: 2 }} />
      ))}
    </LineChart>
  );
}

function renderPie(chart, data, tooltipFormatter) {
  const valueKey = chart.y[0];
  return (
    <PieChart>
      <Tooltip formatter={tooltipFormatter} />
      <Legend />
      <Pie data={data} dataKey={valueKey} nameKey={chart.x} innerRadius="45%" outerRadius="80%"
           // 2px white gaps between slices instead of borders.
           stroke={SURFACE} strokeWidth={2}
           label={({ percent }) => `${(percent * 100).toFixed(1)}%`} labelLine={false}>
        {data.map((entry, i) => (
          <Cell key={entry[chart.x]} fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
        ))}
      </Pie>
    </PieChart>
  );
}
