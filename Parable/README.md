Parable is Python application intended for controlling theatrical flame effects. Used for the Shiva Vista stage at the Burning Man festival and for the annual Compression Fire Arts Festival in Reno, NV.

Used to control an array of propane fire cannons designed and built by Dave King of Controlled Burn, Reno, NV. The electical interface uses an old school PC parallel port, but the I/O class is abstracted so other I/O devices may be subsituted.

The program has several key features:

Multithreaded operation
Import sequences from graphical image files
Both single-shot and repeating (beat) sequences
Tap-beat for syncing patterns to music rhythm
Overlay sequences to create a mashup of effect sequences
Chained I/O devices allow multiple outputs in parallel
Inhereted I/O class used for true screen representation of cannon operation
Parable is built with a Windows UI toolkit but could be adapted to other operating systems.

Dependencies

PythonCard
wxPython
pyparallel (for parallel port operation)
giveio (giveio_setup.exe, hooks I/O interrupts in Windows PC)
PIL
Some slight UI ugliness in the main .pyw file, otherwise well considered code. Hope you agree.

The code posted here may be most useful for looking at ways to run threaded processes concurrently and how to sample data from graphic files.

In it's original configuration, the Shiva Vista fire perfoming stage was surrounded by a ring of 12 fire cannons dubbed "the 12 apostles". This led to the name of this program.