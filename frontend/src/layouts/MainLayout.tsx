import { Outlet } from "react-router-dom";

// Main layout component
// TODO: Implement global layout shell with Navbar and content outlet.
export default function MainLayout() {
  return (
    <div id="main-layout">
      <Outlet />
    </div>
  );
}
