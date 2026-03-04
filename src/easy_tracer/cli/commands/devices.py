"""Device management CLI commands.

Usage:
    easytracer devices list           List connected devices
    easytracer devices list --json    JSON output format
    easytracer devices info -s SERIAL Show device details
"""

from __future__ import annotations

import click

from easy_tracer.cli.output import OutputContext, output_result, output_error, format_table


@click.group()
def devices() -> None:
    """Device management commands."""
    pass


@devices.command("list")
@click.pass_context
def list_devices(ctx: click.Context) -> None:
    """List connected Android devices."""
    from easy_tracer.framework.adb_helper import AdbHelper

    adb: AdbHelper = ctx.obj["adb"]
    output_ctx: OutputContext = ctx.obj["output"]

    if not adb.is_available():
        output_error("ADB not available. Check your adb path.", output_ctx)
        ctx.exit(1)

    device_list = adb.list_devices()

    if output_ctx.json_mode:
        data = [
            {
                "serial": d.serial,
                "status": d.status,
                "model": d.model,
                "product": d.product,
                "device": d.device,
            }
            for d in device_list
        ]
        output_result(output_ctx, data)
    else:
        if not device_list:
            click.echo("No devices connected.")
            return

        headers = ["SERIAL", "STATUS", "MODEL", "PRODUCT"]
        rows = [
            [d.serial, d.status, d.model or "-", d.product or "-"]
            for d in device_list
        ]
        click.echo(format_table(headers, rows))


@devices.command("info")
@click.option("-s", "--serial", required=True, help="Device serial number")
@click.pass_context
def device_info(ctx: click.Context, serial: str) -> None:
    """Show detailed device information."""
    from easy_tracer.framework.adb_helper import AdbHelper

    adb: AdbHelper = ctx.obj["adb"]
    output_ctx: OutputContext = ctx.obj["output"]

    if not adb.is_available():
        output_error("ADB not available.", output_ctx)
        ctx.exit(1)

    devices_list = adb.list_devices()
    device = next((d for d in devices_list if d.serial == serial), None)

    if not device:
        output_error(f"Device {serial} not found.", output_ctx)
        ctx.exit(1)

    model = adb.get_device_model(serial)
    sdk_version = adb.get_sdk_version(serial)

    info = {
        "serial": device.serial,
        "status": device.status,
        "model": model,
        "sdk_version": sdk_version,
        "product": device.product,
        "device": device.device,
        "usb": device.usb,
        "transport_id": device.transport_id,
    }

    if output_ctx.json_mode:
        output_result(output_ctx, info)
    else:
        click.echo(f"Serial:       {info['serial']}")
        click.echo(f"Status:       {info['status']}")
        click.echo(f"Model:        {info['model'] or '-'}")
        click.echo(f"SDK Version:  {info['sdk_version']}")
        click.echo(f"Product:      {info['product'] or '-'}")
        click.echo(f"Device:       {info['device'] or '-'}")
